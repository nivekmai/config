import os
import json
from flask import Flask, request
from flask.ext.restful import Resource, Api

app = Flask(__name__)
api = Api(app)


class Config(Resource):
    def get(self, config_path):
        self.sanitize_path(config_path)
        if not os.path.exists(self.path):
            return {
                'fail': 'file does not exist',
                'file': self.path
            }
        self.load_json()
        return self.json

    def put(self, config_path):
        post_data = request.data
        if not post_data:
            post_data = request.form.keys()[0]
        self.json = str(post_data)
        # return self.json
        self.sanitize_path(config_path)
        #validate json
        if not self.is_valid():
            return {
                'fail': 'invalid json file',
                'data': self.json
            }
        #create path
        path_dir = os.path.dirname(self.path)
        if not os.path.exists(path_dir) and path_dir:
            os.makedirs(path_dir)
        #put the json there
        self.save_json()
        self.load_json()
        return self.json

    def delete(self, config_path):
        self.sanitize_path(config_path)
        try:
            os.remove(self.path)
            try:
                os.rmdir(os.path.dirname(self.path))
            except:
                return {'success': 'file removed, but path still has content'}
            return {'success': 'file and path removed'}
        except:
            return {'fail': 'file does not exist'}

    # Checks to see if self.json is a valid json
    def is_valid(self):
        try:
            json_object = json.loads(self.json)
        except ValueError, e:
            return False
        return True

     # Sanitizes a path, expects a string path, sets the objects path
    def sanitize_path(self, config_path):
        self.path = os.path.join('..',os.path.normpath('/'+config_path).lstrip('/'))

    def save_json(self):
        print self.path
        with open(self.path, 'w') as f:
            f.write(self.json)

    def load_json(self):
        with open(self.path, 'r') as f:
            self.json = json.load(f)


api.add_resource(Config, '/<path:config_path>')

if __name__ == '__main__':
    app.run(debug=True)
