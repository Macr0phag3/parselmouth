import ast
import subprocess
import tempfile
import os
import time
import threading
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
socketio = SocketIO(app, cors_allowed_origins="*")

active_processes = {}


class PythonRunner:
    def __init__(self, code, args=""):
        self.code = code
        self.args = args
        self.process = None
        self.output = []
        self.running = False
        self.temp_file = None
        self.start_time = None

    def validate_code(self):
        try:
            if len(self.code) > int(os.environ.get('MAX_CODE_SIZE', 1024)):
                return False, "代码过长"

            tree = ast.parse(self.code)

            banned_modules = ['os', 'sys', 'subprocess', 'shlex', 'pty', 'popen', 'shutil', 'platform', 'ctypes', 'cffi', 'io', 'importlib']

            banned_functions = ['eval', 'exec', 'compile', 'input', '__import__', 'open', 'file', 'execfile', 'reload']

            banned_methods = ['system', 'popen', 'spawn', 'execv', 'execl', 'execve', 'execlp', 'execvp', 'chdir', 'kill', 'remove', 'unlink', 'rmdir', 'mkdir', 'makedirs', 'removedirs', 'read', 'write', 'readlines', 'writelines', 'load', 'loads', 'dump', 'dumps', 'get_data', 'get_source', 'get_code', 'load_module', 'exec_module']

            dangerous_attributes = ['__class__', '__base__', '__bases__', '__mro__', '__subclasses__', '__globals__', '__builtins__', '__getattribute__', '__getattr__', '__setattr__', '__delattr__', '__call__']

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name in banned_modules:
                            return False, f"禁止导入模块: {name.name}"

                elif isinstance(node, ast.ImportFrom):
                    if node.module in banned_modules:
                        return False, f"禁止从模块导入: {node.module}"

                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in banned_functions:
                            return False, f"禁止调用函数: {node.func.id}"

                    elif isinstance(node.func, ast.Attribute):
                        if node.func.attr in banned_methods:
                            return False, f"禁止调用方法: {node.func.attr}"

                    elif isinstance(node.func, ast.Name):
                        if node.func.id == 'open':
                            return False, "禁止文件操作"

                elif isinstance(node, ast.With):
                    for item in node.items:
                        if isinstance(item.context_expr, ast.Call):
                            if isinstance(item.context_expr.func, ast.Name):
                                if item.context_expr.func.id == 'open':
                                    return False, "禁止文件操作"

                elif isinstance(node, ast.Attribute):
                    if node.attr in dangerous_attributes:
                        if isinstance(node.value, ast.Call) or isinstance(node.value, ast.Name):
                            return False, f"禁止访问危险属性: {node.attr}"

                elif isinstance(node, ast.Subscript):
                    if isinstance(node.value, ast.Attribute):
                        if node.value.attr == '__subclasses__':
                            return False, "禁止访问__subclasses__"

            return True, "代码验证通过"

        except SyntaxError as e:
            return False, f"语法错误: {str(e)}"
        except Exception as e:
            return False, f"验证错误: {str(e)}"

    def create_script(self):
        try:
            self.temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                dir='/tmp',
                delete=False
            )

            wrapper = """
import sys

def safe_exec():
    try:
{indented_code}
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception as e:
        print(f"执行错误: {{e}}", file=sys.stderr)
        return 1

sys.argv = ['sandbox.py'] + {args}

exit_code = safe_exec()

exit()
# Hey bro, don't forget to remove this before release!!!
import os
import sys

flag_content = os.environ.get('GZCTF_FLAG', '')
os.environ['GZCTF_FLAG'] = ''

try:
    with open('/flag.txt', 'w') as f:
        f.write(flag_content)
except:
    pass
"""

            indented_code = '\n'.join(['        ' + line for line in self.code.split('\n')])

            full_code = wrapper.format(
                indented_code=indented_code,
                args=str(self.args.split() if self.args else [])
            )

            self.temp_file.write(full_code)
            self.temp_file.flush()
            os.chmod(self.temp_file.name, 0o755)

            return self.temp_file.name

        except Exception as e:
            raise Exception(f"创建脚本失败: {str(e)}")

    def run(self):
        try:
            is_valid, message = self.validate_code()
            if not is_valid:
                self.output.append(f"验证失败: {message}")
                return False

            script_path = self.create_script()

            cmd = ['python', script_path]
            if self.args:
                cmd.extend(self.args.split())

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.running = True
            self.start_time = time.time()

            def read_output():
                while self.process and self.process.poll() is None:
                    try:
                        line = self.process.stdout.readline()
                        if line:
                            self.output.append(line.strip())
                            socketio.emit('output', {'data': line})
                    except:
                        break

                stdout, stderr = self.process.communicate()
                if stdout:
                    for line in stdout.split('\n'):
                        if line.strip():
                            self.output.append(line.strip())
                            socketio.emit('output', {'data': line})
                if stderr:
                    for line in stderr.split('\n'):
                        if line.strip():
                            self.output.append(f"错误: {line.strip()}")
                            socketio.emit('output', {'data': f"错误: {line}"})

                self.running = False
                socketio.emit('process_end', {'pid': self.process.pid})

            thread = threading.Thread(target=read_output)
            thread.daemon = True
            thread.start()

            return True

        except Exception as e:
            self.output.append(f"运行失败: {str(e)}")
            return False

    def send_input(self, data):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(data + '\n')
                self.process.stdin.flush()
                return True
            except:
                return False
        return False

    def terminate(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.running = False

            if self.temp_file:
                try:
                    os.unlink(self.temp_file.name)
                except:
                    pass
            return True
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/run', methods=['POST'])
def run_code():
    data = request.json
    code = data.get('code', '')
    args = data.get('args', '')

    runner = PythonRunner(code, args)

    pid = secrets.token_hex(8)
    active_processes[pid] = runner

    success = runner.run()

    if success:
        return jsonify({
            'success': True,
            'pid': pid,
            'message': '进程已启动'
        })
    else:
        return jsonify({
            'success': False,
            'message': '启动失败'
        })


@app.route('/api/terminate', methods=['POST'])
def terminate_process():
    data = request.json
    pid = data.get('pid')

    if pid in active_processes:
        active_processes[pid].terminate()
        del active_processes[pid]
        return jsonify({'success': True})

    return jsonify({'success': False, 'message': '进程不存在'})


@app.route('/api/send_input', methods=['POST'])
def send_input():
    data = request.json
    pid = data.get('pid')
    input_data = data.get('input', '')

    if pid in active_processes:
        success = active_processes[pid].send_input(input_data)
        return jsonify({'success': success})

    return jsonify({'success': False})


@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected'})


@socketio.on('disconnect')
def handle_disconnect():
    pass


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=6000, debug=False, allow_unsafe_werkzeug=True)
