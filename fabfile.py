from fabric.api import local

def prepare_deploy():
    commit()
    push()

def push():
    local('git push')

def commit():
    local('git add . && git commit -m "modify something"')
