import paramiko
import sys

def run_remote(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.107', username='raspberrypi5', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print("=== STDOUT ===")
    print(out.encode('ascii', errors='backslashreplace').decode('ascii'))
    if err:
        print("=== STDERR ===")
        print(err.encode('ascii', errors='backslashreplace').decode('ascii'))
    ssh.close()

if __name__ == '__main__':
    cmd = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'echo "connected"'
    run_remote(cmd)
