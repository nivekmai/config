import os
import json
from git import *
from flask import Flask, request
from flask.ext.restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('token', help='API Token', required=True)
parser.add_argument('user', help='Must have username for action', required=True)


TOKEN = '1234'  # Best security code evar!
DATA_LOC = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ), '..', '..', 'config_data')
print DATA_LOC

repo = Repo(
    os.path.join(__file__, '..', '..', '..', 'config_data'),
)
print repo.is_dirty()


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
            return auth_fail()
        return func(*args, **kwargs)
    return auth_and_call


class Config(Resource):

    @auth
    def get(self, config_path):
        '''Gets the JSON from the path.'''
        if not self.split_path(config_path):
            return self.return_obj()
        if not os.path.exists(self.path):
            self.return_code = 404
            self.description = 'File does not exist'
            return self.return_obj()
        if self.load_json():
            return self.json
        return self.return_obj()

    @auth
    def put(self, config_path):
        '''
        Creates or updates the item at the path with the json passed in the post
        data.
        '''
        post_data = request.data
        if not post_data:
            post_data = request.form.keys()[0]
        self.jsons = str(post_data)
        if not self.split_path(config_path):
            return self.return_obj()
        #create path
        self.return_code = 200 if os.path.exists(self.path) else 201
        if not os.path.exists(os.path.dirname(self.path)) and self.project:
            os.makedirs(os.path.dirname(self.path))
        #put the json there
        if not self.save_json():
            return self.return_obj()
        self.load_json()
        self.description = 'File saved successfully'
        return self.return_obj()

    @auth
    def delete(self, config_path):
        '''
        Deletes the file if it exists, path and file if file is the only item in
        the path.
        '''
        self.split_path(config_path)
        if not os.path.exists(self.path):
            self.description = 'File does not exist'
            self.return_code = 404
            return self.return_obj()
        try:
            os.remove(self.path)
        except:
            self.description = 'File exists but could not remove'
        if os.listdir(os.path.dirname(self.path)) == []:
            try:
                os.rmdir(os.path.dirname(self.path))
                self.return_code = 200
                self.description = 'File and path removed'
                return self.return_obj()
            except:
                self.description = 'Path exists but could not remove'
                self.return_code = 500
                return self.return_obj()
        self.return_code = 200
        self.description = 'File removed, but path still has content'
        return self.return_obj()

    def split_path(self, config_path):
        '''
        Sanitizes a path, expects a string path, sets the path, name, and
        project.
        '''
        config_array = config_path.split(os.sep)
        self.project = config_array[0]
        self.name = config_array[-1]
        if (self.project == '..' or self.name == '..' or len(config_array) > 2):
            self.path = 'Invalid'
            self.return_code = 403
            self.description = 'Invalid project and name (expects project/name)'
            return False
        else:
            self.path = os.path.join(
                DATA_LOC, self.project, self.name)
            return True

    def save_json(self):
        '''Checks if the json is valid and saves it.'''
        try:
            self.json = json.loads(self.jsons)
        except ValueError:
            self.return_code = 400
            self.description = 'Invalid json file'
            return False
        with open(self.path, 'w') as f:
            f.write(json.dumps(self.json))
        return True

    def load_json(self):
        '''
        Loads a json, expects an already sanitized path, assumes saved jsons are
        valid.
        '''
        with open(self.path, 'r') as f:
            self.json = json.load(f)

    def return_obj(self):
        '''Bulds an object to return.'''
        return_obj = {
            'description': self.description,
            'path': self.path,
            'name': self.name,
            'project': self.project
        }
        if hasattr(self, 'jsons'):
            return_obj['data'] = self.jsons
        return return_obj, self.return_code

    def git_commit(self, action):
        '''Commits the changes to git.'''
        # TODO:commit changes
        self.git_push()

    def git_push():
        '''Pushes changes upstream.'''
        # TODO: push changes upstream
        pass

api.add_resource(Config, '/<path:config_path>')

if __name__ == '__main__':
    app.run(debug=True)
