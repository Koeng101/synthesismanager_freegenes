import json
from jsonschema import validate

from .models import *
from flask_restplus import Api, Resource, fields, Namespace 
from flask import Flask, abort, request, jsonify, g, url_for, redirect

from .config import SPACES
from .config import BUCKET

from .CRUD import create_crud,requires_auth

###

ns_file = Namespace('files', description='Files')

@ns_file.route('/')
class AllFiles(Resource):
    def get(self):
        return crud_get_list(Files)

@ns_file.route('/<uuid>')
class SingleFile(Resource):
    def get(self,uuid):
        return crud_get(Files,uuid)
    @ns_file.doc('delete_file',security='token')
    @requires_auth(['moderator','admin'])
    def delete(self,uuid):
        file = Files.query.get(uuid)
        SPACES.delete_object(Bucket=BUCKET,Key=file.file_name)
        db.session.delete(file)
        db.session.commit()
        return jsonify({'success':True})


@ns_file.route('/upload')
class NewFile(Resource):
    @ns_file.doc('new_file',security='token')
    @requires_auth(['moderator','admin'])
    def post(self):
        json_file = json.loads(request.files['json'].read())
        file = request.files['file']
        new_file = Files(json_file['name'],file)
        db.session.add(new_file)
        db.session.commit()
        return jsonify(new_file.toJSON())

@ns_file.route('/download/<uuid>')
class DownloadFile(Resource):
    def get(self,uuid):
        obj = Files.query.filter_by(uuid=uuid).first()
        return obj.download()


###
ns_order = create_crud('order','Orders',Order)

