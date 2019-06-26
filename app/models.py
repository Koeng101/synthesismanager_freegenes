from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from flask import Flask, abort, request, jsonify, g, url_for, Response
import uuid

from .config import SPACES
from .config import BUCKET

from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from passlib.apps import custom_app_context as pwd_context

db = SQLAlchemy()
auth = HTTPBasicAuth()

##################
### Validators ###
##################

from jsonschema import validate
import json
import string

# Shared
uuid_regex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
null = {'type': 'null'}

uuid_schema = {'type': 'string','pattern': uuid_regex}
optional_uuid = {'oneOf': [uuid_schema,null]}

generic_string = {'type': 'string'}
optional_string ={'oneOf': [generic_string,null]}

generic_num = { "type": "number" }
optional_num = {'oneOf': [generic_num,null]}

generic_date = {'type': 'string','format':'date-time'}
optional_date = {'oneOf': [generic_date,null]}

name = {'type': 'string','minLength': 3,'maxLength': 30}
tags = {'type': 'array', 'items': optional_string}
force_to_many = {'type': 'array', 'items': uuid_schema}
to_many = {'type': 'array', 'items': {'oneOf': [uuid_schema,null]}}
#many_to_many = {'anyOf': [{'type': 'array','items': uuid},{'type': 'array','items': null}]}

def schema_generator(properties,required,additionalProperties=False):
    return {"$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": additionalProperties}

def base_dict(cls):
    return {"uuid": cls.uuid, "time_created": cls.time_created.isoformat(), "time_updated": cls.time_updated.isoformat()}
###
###
###
class Files(db.Model):
    def __init__(self,name,file):
        file_name = str(uuid.uuid4())
        def upload_file_to_spaces(file,file_name=file_name,bucket_name=BUCKET,spaces=SPACES):
            """
            Docs: http://boto3.readthedocs.io/en/latest/guide/s3.html
            http://zabana.me/notes/upload-files-amazon-s3-flask.html"""
            try:
                spaces.upload_fileobj(file,bucket_name,file_name)
            except Exception as e:
                print("Failed: {}".format(e))
                return False
            return True
        if upload_file_to_spaces(file,file_name=file_name) == True:
            self.name = name
            self.file_name = file_name
    __tablename__ = 'files'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())

    name = db.Column(db.String, nullable=False) # Name to be displayed to user
    file_name = db.Column(db.String, nullable=False) # Link to spaces

    def toJSON(self,full=None):
        return {'uuid':self.uuid,'name':self.name,'file_name':self.file_name}
    def download(self):
        s3 = SPACES
        key = self.file_name
        total_bytes = get_total_bytes(s3,key)
        return Response(
            get_object(s3, total_bytes, key),
            mimetype='text/plain',
            headers={"Content-Disposition": "attachment;filename={}".format(self.name)})

#################
### Job board ###
#################

order_schema = {
        "uuid": uuid_schema,
        "name": generic_string,
        "description": generic_string,
        "status": {"type": "string", "enum": ['Planned','Ordered','Complete','Abandoned']}
        }
order_required = ['name','description','status']
class Order(db.Model):
    validator = schema_generator(order_schema,order_required)
    put_validator = schema_generator(order_schema,[])


    __tablename__ = 'orders'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    pass

geneid_schema = {
        "uuid": uuid_schema,
        "geneid": generic_string,
        "status": generic_string,
        "order_uuid": uuid_schema
        }
geneid_required = ['geneid','order_uuid']
class GeneID(db.Model):
    validator = schema_generator(geneid_schema,geneid_required)
    put_validator = schema_generator(geneid_schema ,[])

    __tablename__ = 'geneids'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    pass

quote_schema = {
        "uuid": uuid_schema,
        "vendor": {"type": "string", "enum": ["Twist","Genscript"]},
        "price": generic_num,
        "order_uuid": uuid_schema,
        "file_uuid": file_uuid,
        "quote_id": generic_string,
        "status": {"type": "string", "enum": ["Pending","Accepted","Rejected"]},
        "geneids": {"type": "array", "items": generic_string},
        }
quote_required = ['vendor','price','order_uuid','file_uuid','quote_id','status','geneids']
class Quote(db.Model):
    validator = schema_generator(quote_schema,quote_required)
    put_validator = schema_generator(quote_schema,[])

    __tablename__ = 'quotes'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    pass

invoice_schema = {
        "uuid": uuid_schema,
        "quote_uuid": uuid_schema,
        "order_uuid": uuid_schema,
        "file_uuid": uuid_schema,
        "invoice_id": generic_string,
        "price": generic_num
        }
invoice_required = ['quote_uuid','order_uuid','file_uuid','invoice_id','price']
class Invoice(db.Model):
    validator = schema_generator(invoice_schema,invoice_required)
    put_validator = schema_generator(invoice_schema,[])

    __tablename__ = 'invoices'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    pass

platemap_schema = {
        "uuid": uuid_schema,
        "file_uuid": uuid_schema,
        "invoice_uuid": uuid_schema,
        "geneids": {"type": "array", "items": generic_string}
        }
platemap_required = ['file_uuid','invoice_uuid','geneids']
class PlateMap(db.Model):
    validator = schema_generator(platemap_schema,platemap_required)
    put_validator = schema_generator(platemap_schema,[])

    __tablename__ = 'platemaps'
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False,default=sqlalchemy.text("uuid_generate_v4()"), primary_key=True)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    pass


