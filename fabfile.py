from fabric.api import local, cd, env

env.hosts = ['zhouyifan.top']



def prepare_deploy():
    commit()
    push()

def push():
    local('git push')

def commit():
    local('git add . && git commit -m "modify something"')


def deploy():
    code_dir = '/home/zhouyifan/spider'
    with cd(code_dir):
        run("git pull")
