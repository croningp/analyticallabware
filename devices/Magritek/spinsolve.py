import os
import socket
import logging
import time

from util import getIPAddresses
from io import BytesIO
from xml.etree.ElementTree import Element, SubElement, Comment, tostring, ElementTree, fromstring

class SpinSolve:
    def __init__(self, nmr_dir, spinsolve_path, port=13000):
        self.nmr_dir = nmr_dir
        self.spinsolve = spinsolve_path
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # get IP address of a network interface
        # assume that only local is up 
        self.host = None
        for addr in getIPAddresses():
            if addr != '0.0.0.0':
                logging.info(f'Trying host IP address {addr}')
            try:
                self.socket.connect((addr, self.port))
                logging.info(f'connected to spinsolve at {addr} port {port}')
                self.host = addr
                break
            except:
                #give some time to server
                logging.warning('No connection could be made to spinsolve at {} port {}'.format(self.host, self.port))
                time.sleep(1)
                continue
        if self.host is None:
            raise ConnectionError()

        # get available protocols
        # constructing xml message
        logging.info('Getting available protocols from spinsolve')
        message = Element('Message')
        message.append(Element('AvailableProtocolsRequest'))
        xml_message = self.serialize(message)
        self.send_message(xml_message)
        
        xml_tree = fromstring(self.recv_message())
        protocols = xml_tree.find('AvailableProtocolsResponse').findall('Protocol')
        self.protocols = [p.text for p in protocols]
        logging.debug(f'Found protocols:\n{self.protocols}')
        self.protocol = None

    def select_protocol(self, protocol):
        '''Select protocol for the next experiment.'''
        if protocol not in self.protocols:
            logging.error('Unknown protocol selected {}'.format(protocol))
            raise ValueError('Unknown protocol selected {}'.format(protocol))
        self.protocol = protocol

    def get_options(self, protocol):
        if protocol not in self.protocols:
            logging.error('Unknown protocol {}'.format(protocol))
            raise ValueError('Unknown protocol selected {}'.format(protocol))
        message = Element('Message')
        option = SubElement(message, "AvailableOptionsRequest")
        option.set('protocol', protocol)
        xml_message = self.serialize(message)
        self.send_message(xml_message)
        print (self.recv_message())
        
    def send_message(self, xml):
        self.socket.sendall(xml)
        logging.debug(f'Message sent:\n{xml}')
        
    def recv_message(self,timeout=10):
        self.socket.settimeout(timeout)
        try:
            response = self.socket.recv(2048)
        except:
            logging.error('Timed out. No response from server received')
            raise
        logging.debug('Response received:\n {}'.format(response))
        return response

    def serialize(self, message):
        f = BytesIO()
        et = ElementTree(message)
        et.write(f, encoding='utf-8', xml_declaration=True) 
        return f.getvalue()

    def run(self):
        if self.protocol == None:
            logging.error('No protocol selected')
            raise Exception('No protocol selected')

        message = Element('Message')
        start = SubElement(message, 'Start')
        start.set('protocol', 'self.protocol')
        xml_message = self.serialize(message)
        self.send_message(xml_message)
