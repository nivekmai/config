import os
import json
import jsonpatch
import jsonpointer
from os import path as p
from git import *
from flask import Flask, request
from flask.ext.restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('token', help='API Token required', required=True)
parser.add_argument('user', help='Must have username for action', required=True)
parser.add_argument('email', help='Must have email for action', required=True)
parser.add_argument('message', help='Commit message')


INIT_CONFIG = p.join(p.dirname(p.abspath(__file__)), '..', 'config.json')
with open(INIT_CONFIG, 'r') as f:
    config = json.load(f)
DATA_LOC = config['data location']
if (p.exists(DATA_LOC)):
    # If setup has been run and the data location is set, load the JSON from
    # there.
    CONFIG = p.join(DATA_LOC, config['project'], 'config.json')
    with open(CONFIG, 'r') as f:
        config = json.load(f)

LOCK = config['lock']
TOKEN = config['token']
repo = Repo(
    DATA_LOC,
)


def auth_fail():
    '''Mock function to make flask-restful happy.'''
    return {'description': 'Authentication failure'}, 401


def get_token():
    '''Gets the token.'''
    return TOKEN


def auth(func):
    '''Decorator, checks if token is good.'''
    def auth_and_call(*args, **kwargs):
        pargs = parser.parse_args()
        if pargs.token != get_token():
            app.logger.debug('Failed token: ' + pargs.token)
            return auth_fail()
        return func(*args, **kwargs)
    return auth_and_call


class Config(Resource):

    def sanitize(func):
        '''
        Sanitizes a path, expects a string path, sets the path, name, and
        project.
        '''

        def split_and_call(self, *args, **kwargs):
            config_path = kwargs['config_path']
            config_array = config_path.split(os.sep)
            try:
                self.project = config_array[0]
                self.file = config_array[1]
                assert self.project != '..'
                assert self.file != '..'
                assert len(config_array) == 2
            except:
                app.logger.warn('config: ' + config_array)
                self.path = 'Invalid'
                self.project = 'Invalid'
                self.file = 'Invalid'
                self.return_code = 403
                self.description = 'Invalid project and name (expects project/name)'
                return self.return_obj()
            self.path = p.join(
                DATA_LOC, self.project, self.file)
            return func(self, *args, **kwargs)
        return split_and_call

    @auth
    @sanitize
    def get(self, config_path):
        '''Gets the JSON from the path.'''
        app.logger.debug('GET: ' + config_path)
        # if not self.split_path(config_path):
        #     return self.return_obj()
        if not p.exists(self.path):
            self.return_code = 404
            self.description = 'File does not exist'
            return self.return_obj()
        if self.load_json():
            return self.json
        self.return_code = 500
        self.description = 'Could not load json'
        return self.return_obj()

    @auth
    @sanitize
    def put(self, config_path):
        '''
        Creates or updates the item at the path with the json passed in the post
        data.
        '''
        app.logger.debug('PUT: ' + config_path)
        if not self.get_json():
            return self.return_obj()
        # if not self.split_path(config_path):
        #     return self.return_obj()
        #create path
        self.return_code = 200 if p.exists(self.path) else 201
        if not p.exists(p.dirname(self.path)) and self.project:
            os.makedirs(p.dirname(self.path))
        #put the json there
        if not self.save_json():
            return self.return_obj()
        self.load_json()
        self.git_commit('add')
        self.description = 'File saved successfully'
        return self.return_obj()

    @auth
    @sanitize
    def delete(self, config_path):
        '''
        Deletes the file if it exists, path and file if file is the only item in
        the path.
        '''
        # if not self.split_path(config_path):
        #     return self.return_obj()
        if not p.exists(self.path):
            self.description = 'File does not exist'
            self.return_code = 404
            return self.return_obj()
        try:
            os.remove(self.path)
        except:
            app.logger.warn('Failed to remove: ' + self.path)
            self.description = 'File exists but could not remove'
        if os.listdir(p.dirname(self.path)) == []:
            try:
                os.rmdir(p.dirname(self.path))
                self.return_code = 200
                self.description = 'File and path removed'
                return self.return_obj()
            except:
                app.logger.warn('Failed to remove: ' + self.path)
                self.description = 'Path exists but could not remove'
                self.return_code = 500
                return self.return_obj()
        self.return_code = 200
        self.description = 'File removed, but path still has content'
        self.git_commit('remove')
        return self.return_obj()

    @auth
    @sanitize
    def patch(self, config_path):
        '''Update only part of a json.'''
        app.logger.debug('Patching: ' + config_path)
        if not self.get_json():
            return self.return_obj()
        patches = json.loads(self.jsons)
        self.load_json()
        app.logger.debug('JSON: ' + json.dumps(self.json))
        app.logger.debug('patches: ' + json.dumps(patches))
        try:
            self.json = jsonpatch.apply_patch(self.json, patches)
        except (
                jsonpatch.JsonPatchConflict,
                jsonpointer.JsonPointerException)as e:
            self.return_code = 422
            self.description = str(e)
            app.logger.error(self.description)
            return self.return_obj()
        except:
            self.return_code = 422
            self.description = 'Unknown error in patch.'
            app.logger.error(self.description)
            return self.return_obj()

        if not self.save_json():
            return self.return_obj()
        self.git_commit('add')
        self.return_code = 200
        self.description = 'File patched successfully'
        return self.return_obj()

    def get_json(self):
        '''Get JSON from request data and validate'''
        post_data = request.data
        if not post_data:
            post_data = request.form.keys()[0]
        self.jsons = str(post_data)
        app.logger.debug('get_json: ' + self.jsons)
        if self.validate_json():
            return True
        return False

    def validate_json(self):
        '''Validates the JSON'''
        try:
            self.json = json.loads(self.jsons)
            return True
        except ValueError:
            self.return_code = 400
            app.logger.warn('Invalid JSON: ' + self.jsons)
            self.description = 'Invalid json file'
            return False

    def save_json(self):
        '''Checks if the json exists and saves it.'''
        if not self.json or self.json == 'null':
            app.logger.warn('Empty JSON on save')
            self.return_code = 500
            self.description = 'Empty JSON on save'
            return False
        with open(self.path, 'w') as f:
            f.write(json.dumps(self.json, indent=4))
        return True

    def load_json(self):
        '''
        Loads a json, expects an already sanitized path, assumes saved jsons are
        valid.
        '''
        with open(self.path, 'r') as f:
            try:
                self.json = json.load(f)
                return True
            except:
                app.logger.warn('Could not load json: ' + self.path)
                return False

    def return_obj(self):
        '''Bulds an object to return.'''
        return_obj = {
            'description': self.description,
            'path': self.path,
            'file': self.file,
            'project': self.project
        }
        if hasattr(self, 'jsons'):
            return_obj['data'] = self.jsons
        return return_obj, self.return_code

    def git_commit(self, action):
        '''Commits the changes to git.'''
        with open(LOCK, 'w'):
            index = repo.index
            relative_path = p.join(self.project, self.file)
            if action is 'add':
                index.add([relative_path])
            elif action is 'remove':
                index.remove([relative_path])
            else:
                raise ValueError('Not a valid git action.')
            pargs = parser.parse_args()
            # TODO: Do this better
            os.environ['GIT_AUTHOR_NAME'] = pargs.user
            os.environ['GIT_AUTHOR_EMAIL'] = pargs.email
            index.commit('' if pargs.message is None else pargs.message)
            self.git_push()

    def git_push(self):
        '''Pushes changes upstream.'''
        origin = repo.remotes.origin
        origin.push()


class List(Resource):

    @auth
    def get(self):
        proj_ob = {}
        projects = os.listdir(DATA_LOC)
        for i in range(len(projects)):
            if projects[i] == ".git":
                continue
            files = os.listdir(p.join(DATA_LOC, projects[i]))
            proj_ob[projects[i]] = []
            for f in range(len(files)):
                proj_ob[projects[i]].append(files[f])
        return proj_ob, 200


api.add_resource(Config, '/api/<path:config_path>')
api.add_resource(List, '/list')

if __name__ == '__main__':
    app.run(debug=True)
