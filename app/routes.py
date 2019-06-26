import json
from jsonschema import validate

import shippo

from .models import *
from flask_restplus import Api, Resource, fields, Namespace 
from flask import Flask, abort, request, jsonify, g, url_for, redirect

from .config import PREFIX
from .config import LOGIN_KEY
from .config import SPACES
from .config import BUCKET
from .config import SHIPPO_KEY
#from dna_designer import moclo, codon

#from .sequence import sequence


###

import os
import jwt
from functools import wraps
from flask import make_response, jsonify
PUBLIC_KEY = os.environ['PUBLIC_KEY']
def requires_auth(roles): # Remove ability to send token as parameter in request
    def requires_auth_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            def decode_token(token):
                return jwt.decode(token.encode("utf-8"), PUBLIC_KEY, algorithms='RS256')
            try:
                decoded = decode_token(str(request.headers['Token']))
            except Exception as e:
                post_token = False
                if request.json != None:
                    if 'token' in request.json:
                        try:
                            decoded = decode_token(request.json.get('token'))
                            post_token=True
                        except Exception as e:
                            return make_response(jsonify({'message': str(e)}),401)
                if not post_token:
                    return make_response(jsonify({'message': str(e)}), 401)
            if set(roles).isdisjoint(decoded['roles']):
                return make_response(jsonify({'message': 'Not authorized for this endpoint'}),401)
            return f(*args, **kwargs)
        return decorated
    return requires_auth_decorator
ns_token = Namespace('auth_test', description='Authorization_test')
@ns_token.route('/')
class ResourceRoute(Resource):
    @ns_token.doc('token_resource',security='token')
    @requires_auth(['user','moderator','admin'])
    def get(self):
        return jsonify({'message': 'Success'})
###



def request_to_class(dbclass,json_request): # Make classmethod
    tags = []
    for k,v in json_request.items():
        if k == 'tags' and v != []:
            dbclass.tags = []
            set_tags = list(set(v))
            for tag in set_tags:

                tags_in_db = Tag.query.filter_by(tag=tag).all()
                if len(tags_in_db) == 0:
                    tags.append(Tag(tag=tag))
                else:
                    tags.append(tags_in_db[0])
            for tag in tags:
                dbclass.tags.append(tag)
        elif k == 'files' and v != []:
            for file_uuid in v:
                files_in_db = File.query.filter_by(uuid=file_uuid).first()
                if len(files_in_db) == 0:
                    pass
                else: 
                    dbclass.files.append(files_in_db[0])
        elif k == 'plates' and v != []:
            dbclass.plates = []
            [dbclass.plates.append(Plate.query.filter_by(uuid=uuid).first()) for uuid in v]
        elif k == 'samples':
            if v != []:
                dbclass.samples = []
                [dbclass.samples.append(Sample.query.filter_by(uuid=uuid).first()) for uuid in v] # In order to sue
        elif k == 'wells' and v != []:
            dbclass.wells = []
            [dbclass.samples.append(Well.query.filter_by(uuid=uuid).first()) for uuid in v]
        elif k == 'platesets' and v != []:
            dbclass.platesets = []
            [dbclass.platesets.append(PlateSet.query.filter_by(uuid=uuid).first()) for uuid in v]
        elif k == 'distributions' and v != []:
            dbclass.distributions = []
            [dbclass.distributions.append(Distribution.query.filter_by(uuid=uuid).first()) for uuid in v]
        else:
            setattr(dbclass,k,v)
    return dbclass

def crud_get_list(cls,full=None):
    return jsonify([obj.toJSON(full=full) for obj in cls.query.all()])

def crud_post(cls,post,database):
    obj = request_to_class(cls(),post)
    database.session.add(obj)
    database.session.commit()
    return jsonify(obj.toJSON())

def crud_get(cls,uuid,full=None,jsonify_results=True):
    obj = cls.query.filter_by(uuid=uuid).first()
    if obj == None:
        return jsonify([])
    if jsonify_results == True:
        return jsonify(obj.toJSON(full=full))
    else:
        return obj

def crud_delete(cls,uuid,database,constraints={}):
    if constraints != {}:
        for constraint in constraints['delete']:
            if cls.query.filter_by(**{constraint: uuid}).first() != None:
                return make_response(jsonify({'message': 'UUID used elsewhere'}),501)
    database.session.delete(cls.query.get(uuid))
    database.session.commit()
    return jsonify({'success':True})

def crud_put(cls,uuid,post,database):
    obj = cls.query.filter_by(uuid=uuid).first()
    updated_obj = request_to_class(obj,post)
    db.session.commit()
    return jsonify(obj.toJSON())

class CRUD():
    def __init__(self, namespace, cls, model, name, constraints={}, security='token',validate_json=False, custom_post=False):
        self.ns = namespace
        self.cls = cls
        self.model = model
        self.name = name
        self.constraints = constraints

        if custom_post == False:
            @self.ns.route('/')
            class ListRoute(Resource):
                @self.ns.doc('{}_list'.format(self.name))
                def get(self):
                    return crud_get_list(cls)
            
                @self.ns.doc('{}_create'.format(self.name),security=security)
                @self.ns.expect(model)
                @requires_auth(['moderator','admin'])
                def post(self):
                    try:
                        request.json
                    except Exception as e:
                        return make_response(jsonify({'message': 'Bad json formatting: {}'.format(e)}),400)
                    if validate_json == True:
                        try:
                            validate(instance=request.get_json(),schema=cls.validator)
                        except Exception as e:
                            return make_response(jsonify({'message': 'Schema validation failed: {}'.format(e)}),400)
                    if 'uuid' in request.get_json():
                        if cls.query.filter_by(uuid=request.get_json()['uuid']).first() == None:
                            return crud_post(cls,request.get_json(),db)
                        else:
                            return make_response(jsonify({'message': 'UUID taken'}),501)
                    return crud_post(cls,request.get_json(),db)
        else:
            print('Custom post and list for {}'.format(name))

        @self.ns.route('/<uuid>')
        class NormalRoute(Resource):
            @self.ns.doc('{}_get'.format(self.name))
            def get(self,uuid):
                return crud_get(cls,uuid)

            @self.ns.doc('{}_delete'.format(self.name),security=security)
            @requires_auth(['moderator','admin'])
            def delete(self,uuid):
                return crud_delete(cls,uuid,db,constraints)

            @self.ns.doc('{}_put'.format(self.name),security=security)
            @self.ns.expect(self.model)
            @requires_auth(['moderator','admin'])
            def put(self,uuid):
                return crud_put(cls,uuid,request.get_json(),db)

        @self.ns.route('/full/')
        class FullListRoute(Resource):
            @self.ns.doc('{}_full'.format(self.name))
            def get(self):
                return crud_get_list(cls,full='full')

        @self.ns.route('/full/<uuid>')
        class FullRoute(Resource):
            @self.ns.doc('{}_full_single'.format(self.name))
            def get(self,uuid):
                return crud_get(cls,uuid,full='full')

        @self.ns.route('/validator')
        class ValidatorRoute(Resource):
            @self.ns.doc('{}_validator'.format(self.name))
            def get(self):
                if validate_json==True:
                    return make_response(jsonify(cls.validator),200)
                return make_response(jsonify({'message': 'No validator for object'}),404)


#========#
# Routes #
#========#
        
###

ns_collection = Namespace('collections', description='Collections')
collection_model = ns_collection.model("collection", {
    "name": fields.String(),
    "readme": fields.String(),
    "tags": fields.List(fields.String),
    "parent_uuid": fields.String()
    })

CRUD(ns_collection,Collection,collection_model,'collection')

@ns_collection.route('/recurse/<uuid>')
class CollectionAllRoute(Resource):
    '''Shows a collection all the way down to the root'''
    @ns_collection.doc('collection_get_all')
    def get(self,uuid):
        '''Get a single collection and everything down the tree'''
        def recursive_down(collection):
            dictionary = collection.toJSON()
            new_parts = []
            for part in collection.parts:
                new_part = part.toJSON()
                new_part['samples'] = [sample.toJSON() for sample in part.samples]
                new_parts.append(new_part)
            dictionary['parts'] = new_parts
            if len(collection.children) > 0:
                dictionary['subcollections'] = [recursive_down(subcollection) for subcollection in collection.children]
            return dictionary
        return jsonify(recursive_down(Collection.query.filter_by(uuid=uuid).first()))

@ns_collection.route('/part_status/<uuid>/<key>')
class CollectionPartStatus(Resource):
    @ns_collection.doc('collection_get_part_status')
    def get(self,key,uuid):
        sql = "SELECT parts.{}, parts.status FROM parts WHERE parts.collection_id='{}'".format(key,uuid)
        result = db.engine.execute(sql)
        dictionary = {}
        for r in result:
            dictionary[str(r[0])] = r[1]
        return jsonify(dictionary)

@ns_collection.route('/part_status/search/<uuid>/<key>/<status>')
class CollectionPartStatus(Resource):
    @ns_collection.doc('collection_get_part_status_search')
    def get(self,key,uuid,status):
        sql = "SELECT parts.{}, parts.status FROM parts WHERE parts.collection_id='{}' AND parts.status='{}'".format(key,uuid,status)
        result = db.engine.execute(sql)
        dictionary = {}
        for r in result:
            dictionary[str(r[0])] = r[1]
        return jsonify(dictionary)

###

ns_part = Namespace('parts', description='Parts')
part_model = ns_part.model("part", {
    "name": fields.String(),
    "description": fields.String(),
    "tags": fields.List(fields.String),
    "gene_id": fields.String(),
    "part_type": fields.String(), # TODO enum
    "original_sequence": fields.String(),
    "optimized_sequence": fields.String(),
    "synthesized_sequence": fields.String(),
    "full_sequence": fields.String(),
    "genbank": fields.Raw(),
    "vector": fields.String(),
    "primer_for": fields.String(),
    "primer_rev": fields.String(),
    "barcode": fields.String(),
    "vbd": fields.String(),
    "translation": fields.String(),
    "collection_id": fields.String(),
    "author_uuid": fields.String(),
    "ip_check": fields.String(),
    "ip_check_date": fields.DateTime(),
    "ip_check_ref": fields.String()
    })
CRUD(ns_part,Part,part_model,'part')
@ns_part.route('/get/<key>/<value>')
class PartGeneId(Resource):
    def get(self,key,value):
        kwargs = {key:value}
        parts = Part.query.filter_by(**kwargs)
        if parts.count() == 0:
            return jsonify([])
        else:
            return jsonify([part.toJSON() for part in parts])

@ns_part.route('/collection/<uuid>')
class PartCollection(Resource):
    def get(self,uuid):
        return jsonify([obj.toJSON() for obj in Part.query.filter_by(collection_id=uuid)])

@ns_part.route('/locations/<uuid>')
class PartLocations(Resource):
    def get(self,uuid):
        obj = Part.query.filter_by(uuid=uuid).first()
        results = []
        for sample in obj.samples:
            for well in sample.wells:
                plate = well.plate.toJSON()
                plate['wells'] = well.toJSON()
                results.append(plate)
        return jsonify(results)

###

ns_part_modifiers = Namespace('part_modification', description='Modify parts')


def next_gene_id():
    result = db.engine.execute("SELECT parts.gene_id FROM parts WHERE gene_id IS NOT NULL ORDER BY gene_id DESC LIMIT 1")
    for r in result:
        last_id = r
    last_num = int(last_id[0][-6:])
    print(last_num)
    new_id = PREFIX + str(last_num+1).zfill(6)
    return new_id

@ns_part.route('/next_gene_id')
class NextGeneId(Resource):
    def get(self):
        return jsonify({'gene_id': next_gene_id()})

@ns_part_modifiers.route('/gene_id/<uuid>')
class NewGeneID(Resource):
    @ns_part.doc('new_gene_id',security='token')
    @requires_auth(['moderator','admin'])
    def put(self,uuid):
        obj = Part.query.filter_by(uuid=uuid).first()
        obj.gene_id = next_gene_id()
        db.session.commit()
        return jsonify(obj.toJSON())

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
        print(type(SPACES))
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

ns_author = Namespace('authors', description='Authors')
author_model = ns_part.model("author", {
    "name": fields.String(),
    "email": fields.String(),
    "tags": fields.List(fields.String),
    "affiliation": fields.String(),
    "orcid": fields.String(), # TODO enum
    })
CRUD(ns_author,Author,author_model,'author')

###

ns_organism = Namespace('organisms', description='Organisms')
organism_model = ns_organism.model("organism", {
    "name": fields.String(),
    "description": fields.String(),
    "tags": fields.List(fields.String),
    "genotype": fields.String(),
    })
CRUD(ns_organism,Organism,organism_model,'organism')

###
###
###

ns_protocol = Namespace('protocols', description='Protocols')
protocol_model = ns_protocol.schema_model('protocol', Protocol.validator)
CRUD(ns_protocol,Protocol,protocol_model,'protocol',validate_json=True)

###

ns_plate = Namespace('plates', description='Plates')
plate_model = ns_plate.schema_model('plate', Plate.validator)
CRUD(ns_plate,Plate,plate_model,'plate',validate_json=True)

def plate_recurse(uuid):
    obj = Plate.query.filter_by(uuid=uuid).first()
    wells = []
    for well in obj.wells:
        samples = []
        for sample in well.samples:
            to_add = sample.toJSON()
            to_add['part'] = sample.part.toJSON()
            samples.append(to_add)
        to_add = well.toJSON()
        to_add['samples'] = samples
        wells.append(to_add)
    plate = obj.toJSON()
    plate['wells'] = wells
    return plate

@ns_plate.route('/recurse/<uuid>')
class PlateSamples(Resource):
    def get(self,uuid):
        return jsonify(plate_recurse(uuid))

###

ns_sample = Namespace('samples', description='Samples')
sample_model = ns_sample.schema_model('sample', Sample.validator)
CRUD(ns_sample,Sample,sample_model,'sample',constraints={'delete': ['derived_from']},validate_json=True)

###

ns_well = Namespace('wells', description='Wells')
well_model = ns_well.schema_model('well', Well.validator)
CRUD(ns_well,Well,well_model,'well',validate_json=True)

@ns_well.route('/plate_recurse/<uuid>')
class WellToPlate(Resource):
    def get(self,uuid):
        plate_uuid = Well.query.filter_by(uuid=uuid).first().toJSON()['plate_uuid']
        return jsonify(plate_recurse(plate_uuid))

###
###
###

ns_operator = Namespace('operators', description='Operators')
operator_model = ns_operator.schema_model('operator', Operator.validator)
CRUD(ns_operator,Operator,operator_model,'operator',validate_json=True)

ns_plan = Namespace('plans',description='Plans')
plan_model = ns_plan.schema_model('plan', Plan.validator)
CRUD(ns_plan,Plan,plan_model,'plan',validate_json=True)

ns_plateset = Namespace('plateset',description='PlateSets')
plateset_model = ns_plateset.schema_model('plateset',PlateSet.validator)
CRUD(ns_plateset,PlateSet,plateset_model,'plateset',validate_json=True)

ns_distribution = Namespace('distribution',description='Distributions')
distribution_model = ns_distribution.schema_model('distribution',Distribution.validator)
CRUD(ns_distribution,Distribution,distribution_model,'distribution',validate_json=True)

ns_order = Namespace('order',description='Orders')
order_model = ns_order.schema_model('order',Order.validator)
CRUD(ns_order,Order,order_model,'order',validate_json=True)

ns_institution = Namespace('institution',description='Institutions')
institution_model = ns_institution.schema_model('institution',Institution.validator)
CRUD(ns_institution,Institution,institution_model,'institution',validate_json=True)

ns_materialtransferagreement = Namespace('materialtransferagreement',description='MaterialTransferAgreements')
materialtransferagreement_model = ns_materialtransferagreement.schema_model('materialtransferagreement',MaterialTransferAgreement.validator)
CRUD(ns_materialtransferagreement,MaterialTransferAgreement,materialtransferagreement_model,'materialtransferagreement',validate_json=True)

###
class ShippoCRUD():
    def __init__(self, namespace, cls, model, name, create_func, security='token',validate_json=True):
        self.ns = namespace
        self.cls = cls
        self.model = model
        self.name = name

        @self.ns.route('/')
        class ListRoute(Resource):
            @self.ns.doc('{}_list'.format(self.name),security=security)
            @requires_auth(['moderator','admin'])
            def get(self):
                return crud_get_list(cls)

            @self.ns.doc('{}_create'.format(self.name),security=security)
            @self.ns.expect(model)
            @requires_auth(['moderator','admin'])
            def post(self):
                if validate_json == True:
                    try:
                        validate(instance=request.get_json(),schema=cls.validator)
                    except Exception as e:
                        return make_response(jsonify({'message': 'Schema validation failed: {}'.format(e)}),400)
                if 'uuid' in request.get_json():
                    if cls.query.filter_by(uuid=request.get_json()['uuid']).first() == None:
                        return crud_post(cls,request.get_json(),db)
                    else:
                        return make_response(jsonify({'message': 'UUID taken'}),501)

                inc_req = request.get_json()
                inc_req['api_key'] = SHIPPO_KEY

                if name == 'address':
                    if 'zip_code' in inc_req: # handle address zips correctly
                        inc_req['zip'] = inc_req.pop('zip_code')
                    inc_req['validate'] = True

                if name == 'shipment':
                    try:
                        address_from = Address.query.filter_by(uuid=inc_req['address_from']).first().toJSON()
                        address_to = Address.query.filter_by(uuid=inc_req['address_to']).first().toJSON()
                        parcel = Parcel.query.filter_by(uuid=inc_req['parcel_uuid']).first().toJSON()
                    except Exception as e:
                        print(e)
                        return make_response(jsonify({'message': 'UUID for address_from, address_to, or parcel was not found'}),501)
                    obj = create_func(address_from=address_from['object_id'], address_to=address_to['object_id'], parcels=parcel['object_id'],api_key=SHIPPO_KEY)

                else:
                    obj = create_func(**inc_req)
                inc_req['object_id'] = obj['object_id']

                if name == 'address':
                    inc_req['zip_code'] = inc_req.pop('zip')
                    if obj['validation_results']['is_valid'] != True:
                        return make_response(jsonify({'message': 'Address validation failed'}),501)
                if name == 'parcel':
                    print(obj)
                    if obj['object_state'] != 'VALID':
                        return make_response(jsonify({'message': 'Parcel validation failed'}),501)

                return crud_post(cls,inc_req,db)

ns_address = Namespace('address',description='Addresss')
address_model = ns_address.schema_model('address',Address.validator)
CRUD(ns_address,Address,address_model,'address',validate_json=True,custom_post=True)
ShippoCRUD(ns_address,Address,address_model,'address',shippo.Address.create)

ns_parcel = Namespace('parcel',description='Parcels')
parcel_model = ns_parcel.schema_model('parcel',Parcel.validator)
CRUD(ns_parcel,Parcel,parcel_model,'parcel',validate_json=True,custom_post=True)
ShippoCRUD(ns_parcel,Parcel,parcel_model,'parcel',shippo.Parcel.create)


ns_shipment = Namespace('shipment',description='Shipments')
shipment_model = ns_shipment.schema_model('shipment',Shipment.validator)
CRUD(ns_shipment,Shipment,shipment_model,'shipment',validate_json=True,custom_post=True)
ShippoCRUD(ns_shipment,Shipment,shipment_model,'shipment',shippo.Shipment.create)

@ns_shipment.route('/rates/<uuid>')
class ShipmentRates(Resource):
    @ns_shipment.doc('get_rates',security='token')
    @requires_auth(['moderator','admin'])
    def get(self,uuid):
        obj = Shipment.query.filter_by(uuid=uuid).first().toJSON()
        rates = shippo.Shipment.retrieve(obj['object_id'],api_key=SHIPPO_KEY)['rates']
        return jsonify(rates)


transactioncreate_model = ns_shipment.model("transactioncreate", {
    "rate_id": fields.String(),
    })

@ns_shipment.route('/create_label/<uuid>')
class TransactionCreate(Resource):
    @ns_shipment.doc('create_label',security='token')
    @requires_auth(['moderator','admin'])
    @ns_shipment.expect(transactioncreate_model)
    def post(self,uuid):
        obj = Shipment.query.filter_by(uuid=uuid).first()
        if obj == None:
            return jsonify([])
        trans_obj = shippo.Transaction.create(rate=request.get_json()['rate_id'],label_file_type="PDF",api_key=SHIPPO_KEY)
        if trans_obj['object_state'] != 'VALID':
            return make_response(jsonify({'message': 'Object state of transaction is not valid'}),501)

        obj.transaction_id = trans_obj['object_id']
        db.session.commit()
        return jsonify(obj.toJSON())

@ns_shipment.route('/retrieve_transaction/<uuid>')
class TransactionView(Resource):
    @ns_shipment.doc('retrieve_transaction',security='token')
    @requires_auth(['moderator','admin'])
    def get(self,uuid):
        obj = Shipment.query.filter_by(uuid=uuid).first()
        if obj == None:
            return jsonify([])
        trans_obj = shippo.Transaction.retrieve(obj.transaction_id, api_key=SHIPPO_KEY)
        return jsonify({"label_url": trans_obj['label_url'], "tracking_number": trans_obj['tracking_number'], "tracking_url_provider": trans_obj["tracking_url_provider"]})





