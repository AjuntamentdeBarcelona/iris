from integrations.services.gcod.config import service_name, Streets, Districts, Type_Streets, Neighborhood, \
    Neighborhood_District, Validate_Adress_var, Validate_Adress_cod, get_dades_xy
from ..RestClient.integrate import ApiConnectClient
import logging


class GcodServices(ApiConnectClient):

    def __init__(self):
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)

    def streets(self, variable=''):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        if variable:
            params = {"variante": variable}
            data = data.get(extension=Streets, params=params)
        else:
            data = data.get(extension=Streets)
        self.logger.info('Get request to Control')
        return data

    def districts(self):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        data = data.get(extension=Districts)
        self.logger.info('Get request to Control')
        return data

    def type_streets(self):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        data = data.get(extension=Type_Streets)
        self.logger.info('Get request to Control')
        return data

    def neighborhood(self):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        data = data.get(extension=Neighborhood)
        self.logger.info('Get request to Control')
        return data

    def neighborhood_codi(self, codi_neighborhood):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        data = data.get(extension=Neighborhood+'/'+codi_neighborhood)
        self.logger.info('Get request to Control')
        return data

    def neighborhood_district(self, codi_district):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        data = data.get(extension=Neighborhood_District + codi_district)
        self.logger.info('Get request to Control')
        return data

    def adress_validation_variable(self, street_variable, numIni, numFin='', lletraIni='', tipusVia='', tipusNum='',
                                   tipusSeq='', exacta='', nullCoord='S', maxRegs=100):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        params = {'variant': street_variable,
                  'numIni': numIni.strip(),
                  'numFin': numFin.strip(),
                  'lletraIni': lletraIni,
                  'tipusVia': tipusVia,
                  'tipusNum': tipusNum,
                  'tipusSeq': tipusSeq,
                  'exacta': exacta,
                  'nullCoord': nullCoord,
                  'maxRegs': maxRegs,
                  }
        self.logger.info(params)
        data = data.get(extension=Validate_Adress_var, params=params)
        self.logger.info(data)
        if data['ReturnCode'] == 1:
            neighborhood_data = self.neighborhood_codi(data['Data'][0]['BARRI'])
            self.logger.info(neighborhood_data)
            json = data['Data'][0]
            json['BARRI_NOM'] = neighborhood_data['Data'][0]['DESCRIPCION']
            district_id = json['DISTRICTE']
            if district_id and district_id != '11':
                json['DISCTRICTE'] = int(district_id)
            data['Data'] = [json]
            self.logger.info(data)
            self.logger.info('Get request to Control')
        return data

    def adress_validation_code(self, street_code, numIni, numFin='', lletraFin='', tipusVia='', tipusNum='',
                               tipusSeq='', exacta='', nullCoord='S', maxRegs=100):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        params = {'codiCarrer': street_code,
                  'numIni': numIni,
                  'numFin': numFin,
                  'lletraFin': lletraFin,
                  'tipusVia': tipusVia,
                  'tipusNum': tipusNum,
                  'tipusSeq': tipusSeq,
                  'exacta': exacta,
                  'nullCoord': nullCoord,
                  'maxRegs': maxRegs,
                  }
        data = data.get(extension=Validate_Adress_cod, params=params)
        self.logger.info('Get request to Control')
        return data

    def get_dades_xy(self, zona, x, y):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        return data.get(extension=get_dades_xy, params={
            'tipus': zona,
            'coordenadaX': x,
            'coordenadaY': y
        })

    def get_offset_xy(self, address_code, num, distance):
        data = ApiConnectClient(self.service_name, logger=self.logger)
        return data.get(extension='GeoDadesXy/GetOffsetXY', params={
            'Codigo': address_code,
            'NumIni': num,
            'NumFin': num,
            'Distancia': distance,
        })

    def get_position_xy_lots(self, position_array):
        json = {"data": position_array}
        self.logger.info(json)
        data = ApiConnectClient('Georest', logger=self.logger)
        data = data.post(extension='dadesxy/xylots', json=json)
        self.logger.info(data)
        if data.status_code == 400:
            return {}
        return data.json()

    def get_street_data(self, codi):
        params = {"codi": codi}
        data = ApiConnectClient('Georest', logger=self.logger)
        data = data.get(extension='carrers/codi', params=params)
        return data
