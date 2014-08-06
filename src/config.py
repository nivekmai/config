import os
import json
from flask import Flask, request
from flask.ext.restful import Resource, Api

app = Flask(__name__)
api = Api(app)


class Config(Resource):
    def get(self, config_path):
        if not self.split_path(config_path):
            return self.return_obj()
        if not os.path.exists(self.path):
            self.description = 'File does not exist'
            self.return_code = 404
            return self.return_obj()
        if self.load_json():
            return self.json
        return self.return_obj()

    def put(self, config_path):
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

    def delete(self, config_path):
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

     # Sanitizes a path, expects a string path, sets the path, name, and project
    def split_path(self, config_path):
        config_array = config_path.split(os.sep)
        self.project = config_array[0]
        self.name = config_array[-1]
        if (self.project == '..' or self.name == '..' or len(config_array) > 2):
            self.path = 'Invalid'
            self.description = 'Invalid project and name (expects project/name)'
            self.return_code = 403
            return False
        else:
            self.path = os.path.join('..', self.project, self.name)
            return True

    # Checks if the json is valid and saves it
    def save_json(self):
        try:
            self.json = json.loads(self.jsons)
        except ValueError:
            self.return_code = 400
            self.description = 'Invalid json file'
            return False
        with open(self.path, 'w') as f:
            f.write(json.dumps(self.json))
        return True

    # Loads a json, expects an already sanitized path
    def load_json(self):
        with open(self.path, 'r') as f:
            self.json = json.load(f)

    # Bulds an object to return
    def return_obj(self):
        return_obj = {
            'description': self.description,
            'path': self.path,
            'name': self.name,
            'project': self.project
        }
        if hasattr(self, 'jsons'):
            return_obj['data'] = self.jsons
        return return_obj, self.return_code

api.add_resource(Config, '/<path:config_path>')

if __name__ == '__main__':
    app.run(debug=True)
