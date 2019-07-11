#!/usr/bin/env python
# coding: utf-8

import threading, socket, time, logging
import xml.etree.ElementTree as ET

#from queue import Queue
from io import BytesIO


class MiniSpinsolve:
    '''
    The current class provides several remote control options for 
    Magritec Spinsolve NMR instrument. All the commands are based on the
    operating manual for software version 1.13 and were tested on the 
    Spinsolve Carbon 80 NMR spectrometer
    '''
    
    def __init__(self, HOST=None, PORT=13000, *, magritec_path=None, nmr_path=None):
        '''
        Initializer for the Spinsolve class
        
        Args:
            HOST (str): TCP/IP address of the local host
            PORT (int): TCP/IP listening port for Spinsolve software, 13000 by defualt
                must be changed in the software if necessary
            magritec_path (str): system path for the location of the remote control
                options file created by Spinsolve software at start up, by defualt:
                "MyDocuments\\Magritec\\Spinsolve"
            nmr_path (str): system path for saving the acquired NMR spectrums
            
            *small warning sign here* to avoid confusion magritec_path and nmr_path, if provided, must be
            used only as keyword arguments
        '''
        
        # getting the localhost IP address if not provided by instantiation
        # refer to socket module manual for details
        try:
            CURR_HOST = socket.gethostbyname(socket.getfqdn())
        except:
            CURR_HOST = socket.gethostbyname(socket.gethostname())
        
        # system variables
        self.HOST = HOST or CURR_HOST
        self.PORT = PORT
        self.BUFSIZE = 8192
        self.magritec_path = magritec_path
        
        # if nmr_path is not provided, spectrums will be saved in C:\NMRs
        self.nmr_path = nmr_path or 'C:\\NMRs'
        
        # class logger
        self.logger = logging.getLogger('spinsolve_logger')
        
        # creating a socket client
        self._spinsolve_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # connecting to a socket client
        # it will try to connect 3 times waiting 60 seconds in between attempts
        # if an error occurs
        for i in range(3):
            try:
                self._spinsolve_client.connect((self.HOST, self.PORT))
                break
            except Exception as E:
                self.logger.debug(f'connection error: {E}')
                time.sleep(60)
                continue
        
        # spawning and starting the thread for receiving messages
        self._receiving_thread = threading.Thread(target=self._receive, name='Spinsolve data receiving thread', daemon=True)
        self._receiving_thread.start()
        
        # selected documented commands for easier maintanance
        self.SIMPLE_PROTON_PROTOCOL = '1D PROTON'
        self.SIMPLE_PROTON_PROTOCOL_OPTIONS = ('QuickScan', 'StandardScan', 'PowerScan')
        self.SAMPLE_SHIM_PROTOCOL = 'SHIM 1H SAMPLE'
        self.SAMPLE_SHIM_PROTOCOL_OPTIONS = ['CheckShim',
                                             'LockAndCalibrateOnly',
                                             'QuickShim1',
                                             'QuickShim2',
                                             'QuickShimAll',
                                             'PowerShim']
        # USER_FOLDER_TYPES specifies where the obtained spectrums will be saved:
        # "UserFolder" will save the data in the folder provided by nmr_path attribute
        # "TimeStamp" will save data in new folders as (yyyymmddhhmmss) in nmr_path folder
        # "TimeStampTree" will save the data in the set of timestamped folders as yyyy\mm\dd\hhmmss
        self.USER_FOLDER_TYPES = ['UserFolder',
                                  'TimeStamp',
                                  'TimeStampTree']
        
        self._self_check()
        self.user_folder()
    
    def __del__(self):
        '''
        Method for removing the class instance
        '''        
        
        # closing connection
        self._spinsolve_client.close()
        self.logger.debug('connection closed')
        
        # killing the receiving thread
        # should be dead anyway by dropping the connection
        # but with threads you never know
        time.sleep(3)
        try:
            self.logger.info('waiting for receiving thread')
            self._receiving_thread.join()
            self.logger.info('receiving thread dead')
        except:
            pass
    
    def __msg_serializer(self, command, command_attrib={}, command_option=None, option_options={}, *args):
        '''
        Internal method for message serialization. Return an XML tree as a bytes object
        
        *small warning sign here* as an internal class method it doesn't check
        the supplied arguments and should not be used on class instances
        
        Args:
            command (str): main command to be sent to instrument
            command_options (dict): otions for the main command, empty dict by default
            command_option (str): pretty self-describing
            option_options (dict): options for the command_option
            arg in args (dict): (optional) other options
        '''
        
        # empty bytes object for message building
        msg = BytesIO()
        
        # <Message /> root for the message
        msg_root = ET.Element('Message')
        
        # first element of the message root as <"command"/> 
        # with attributes as "command_option_key"="command_option_value"
        msg_root_command = ET.SubElement(msg_root, command, command_attrib)
        
        # if provided, optional subelement for the command as <"command_option"/>
        # with attributes as "option_options_key"="option_options_value"
        msg_root_command_option = ET.SubElement(msg_root_command, command_option, option_options)
        
        # if additional options required
        for arg in args:
            msg_root_command_option_optional = ET.SubElement(msg_root_command, command_option, arg)
        
        # growing a message XML tree with the <Message /> root
        msg_tree = ET.ElementTree(msg_root)
        
        # writing the message tree to msg object
        msg_tree.write(msg, encoding='utf-8', xml_declaration=True)
        
        # getting the value
        message = msg.getvalue()
        
        return message
    
    def __msg_parser(self, data_root, tag):
        '''
        An internal method for parsing the messages received from the instruments and logging valuable information
        
        *small warning sign here* as an internal class method it doesn't check
        the supplied arguments and should not be used on class instances
        
        Args:
            data_root (XML element): an XML root element parsed from the incoming message
            tag (str): main element tag for indicating the valuable information
        '''
        
        # checking for the self-check response
        if 'Hardware' in tag:
            # getting the main element from the data_root
            main_element = data_root.find(f'.//{tag}')
            
            # looking for connection to the instrument
            connected_tag = main_element.find('.//ConnectedToHardware').text
            if connected_tag == 'false':
                self.logger.critical('The NMR instrument is not connected, try to reconnect it and run _self_check method again')
                ET.dump(data_root)
                return
            
            # looking for the software version
            software_tag = main_element.find('.//SpinsolveSoftware').text
            
            # looking for the instrument model
            spinsolve_tag = main_element.find('.//SinsolveType').text or '"No instrument"'
            
            # logging the acquired information
            self.logger.debug(f'The {spinsolve_tag} NMR instrument is successfully connected')
            self.logger.debug(f'Running under Spinsolve software version {software_tag}')
            if software_tag[:4] != '1.13':
                self.logger.debug('Current software version {} was not tested, use at your own risk'.format(software_tag))
        
        # TODO parse every type of responses
        else:
            ET.dump(data_root)
    
    def _receive(self):
        '''
        Internal method for receiving messages from Spinsolve server
        '''
        
        while True:
            try:
                # receiving data
                data = self._spinsolve_client.recv(self.BUFSIZE)
                
                # logging the raw message
                # mainly for debugging reasons
                self.logger.info(data.decode())
                
                # creating bytes object for future parsing
                data_obj = BytesIO(data)
                                
                try:
                    # parsing the obtained message
                    data_tree = ET.parse(data_obj)
                    data_root = data_tree.getroot()
                    
                    # getting the main element tag
                    # looking for all children elements and writing the tag of the first obtained
                    data_tag = data_root.find('.//').tag
                    
                    #calling parser for valuable information logging
                    self.__msg_parser(data_root, data_tag)
                    
                    # printing the message in the console
                    # TODO separate method for message parsing and logging the valuable information
                    # ET.dump(data_root)
                    
                except Exception as exc:
                    # workaround the parsing errors
                    # sometimes server sends invalid XML messages with several XML roots
                    # that causes the error in parsing process
                    # in this case the message will be displayed in raw format
                    self.logger.debug(f'parsing error: {exc}')
                    self.logger.debug('raw message:\n', data.decode())
                    continue
                
            except Exception as exc:
                # in case connection problems
                self.logger.debug(exc)
                break
    
    def _self_check(self):
        '''
        An internal method for checking the connection and current version of the NMR instrument
        '''
        
        # building the message
        check_msg = self.__msg_serializer('HardwareRequest')
        
        try:
            self._spinsolve_client.sendall(check_msg)
        except Exception as E:
            self.logger.critical(f'some error occured: {E}')
    
    def proton(self, option):
        '''
        Method for running the simple 1D proton experiment
        
        Args:
            option (str): scan type for the 1D PROTON protocol aviable from SIMPLE_PROTON_PROTOCOL_OPTIONS
        '''
        
        # validating provided option
        if option in self.SIMPLE_PROTON_PROTOCOL_OPTIONS:
            # building 1D PROTON protocol message
            proton_msg = self.__msg_serializer(
                    'Start', 
                    {'protocol': self.SIMPLE_PROTON_PROTOCOL},
                    'Option',
                    {'name': 'Scan', 'value': f'{option}'}
                    )
            
            # for debugging reasons:
            self.logger.info(proton_msg.decode())
            
            # sending the message
            try:
                self._spinsolve_client.sendall(proton_msg)
                self.logger.debug(f'should start the {option} 1D proton nmr experiment')
            except Exception as E:
                self.logger.critical(f'some error occured: {E}')
        else:
            self.logger.debug('selected option is not valid')

        
    def shim(self, option, reference_peak):
        '''
        Method for shimming the instrument to the provided reference peak
        
        Args:
            option (str): shimming type, available from SAMPLE_SHIM_PROTOCOL_OPTIONS
            reference_peak (float): largest peak of the supplied sample
                used for the calibration of the ppm scale during shimming
        '''
        
        if option in self.SIMPLE_PROTON_PROTOCOL_OPTIONS:
            # building shimming protocol message
            shimming_msg = self.__msg_serializer('Start', 
                                                 {'protocol': self.SAMPLE_SHIM_PROTOCOL},
                                                 'Option',
                                                 {'name': 'SampleReference', 'value': f'{reference_peak}'},
                                                 {'name': 'Shim', 'value': f'{option}'}
                                                 )
            # for debugging reasons
            self.logger.info(shimming_msg.decode())
            
            # sending the message
            try:
                self._spinsolve_client.sendall(shimming_msg)
                self.logger.debug(f'should start the {option} shimming procedure, calibrating for {reference_peak} peak')
            except Exception as E:
                self.logger.critical(f'some error occured: {E}')
        else:
            self.logger.debug('selected option is not valid')
        
    def user_data(self, *, solvent, sample):
        '''
        Method for setting the user parameters in the Spinsolve software
        
        Args:
            solvent (str): solvent name to be saved with the spectrum data
            sample (str): sample name to be saved with the spectrum data
            
            *small warning sign here* to avoid confusion, solvent and sample must be provided as keyword arguments
        '''
        
        # since the command uses XML element text instead of attributes
        # for setting the parameters, the method does not call __msg_serializer to 
        # build the XML message and is building the message itself, so
        # the following code is not commented, refer to __msg_serializer method for details
        try:
            msg_solvent = BytesIO()
            msg_solvent_root = ET.Element('Message')
            msg_solvent_root_protocol = ET.SubElement(msg_solvent_root, 'Set')
            msg_solvent_root_protocol_option = ET.SubElement(msg_solvent_root_protocol, 'Solvent')
            msg_solvent_root_protocol_option.text = solvent
            msg_solvent_tree = ET.ElementTree(msg_solvent_root)
            msg_solvent_tree.write(msg_solvent, encoding='utf-8', xml_declaration=True)
            message_solvent = msg_solvent.getvalue()
            
            msg_sample = BytesIO()
            msg_sample_root = ET.Element('Message')
            msg_sample_root_protocol = ET.SubElement(msg_sample_root, 'Set')
            msg_sample_root_protocol_option = ET.SubElement(msg_sample_root_protocol, 'Sample')
            msg_sample_root_protocol_option.text = solvent
            msg_sample_tree = ET.ElementTree(msg_sample_root)
            msg_sample_tree.write(msg_sample, encoding='utf-8', xml_declaration=True)
            message_sample = msg_sample.getvalue()
            
            self.logger.info(message_solvent)
            self.logger.info(message_sample)
            
            try:
                self._spinsolve_client.sendall(message_solvent)
                self._spinsolve_client.sendall(message_sample)
            except Exception as E:
                self.logger.critical(f'some error occured:{E}')
        except TypeError:
            self.logger.critical('the method must be called with keyword arguments')

    def user_folder(self, data_folder_type='TimeStamp'):
        '''
        Method for setting the path from nmr_path as a destination folder for saving 
        the data obtained from the NMR instrument
        
        Args:
            data_folder_type (str): specifies where the obtained spectrums will be saved. Following values are possible:
                "UserFolder" will save the data in the folder provided by nmr_path argument
                "TimeStamp" will save data in new folders as (yyyymmddhhmmss) in nmr_path folder (default)
                "TimeStampTree" will save the data in the set of timestamped folders as yyyy\mm\dd\hhmmss
        '''
        
        # as for user_data method, the following code is not commented
        # refer above methods for details
        msg = BytesIO()
        msg_root = ET.Element('Message')
        msg_root_protocol = ET.SubElement(msg_root, 'Set')
        msg_root_protocol_option = ET.SubElement(msg_root_protocol, 'DataFolder')
        msg_root_protocol_option_option = ET.SubElement(msg_root_protocol_option, f'{data_folder_type}')
        msg_root_protocol_option_option.text = self.nmr_path
        msg_tree = ET.ElementTree(msg_root)
        msg_tree.write(msg, encoding='utf-8', xml_declaration=True)
        message = msg.getvalue()
        
        self.logger.info(message)
        try:
            self._spinsolve_client.sendall(message)
        except Exception as E:
            self.logger.critical(f'some error occured:{E}')

    def estimate_duration(self, option):
        '''
        Method for estimating the duration for the selected protocol
        Currently supports only 1D PROTON
        
        Args:
            option (str): scan option value for the 1D proton protocol
        '''
        # validating the option for the 1D proton protocol
        if option in self.SIMPLE_PROTON_PROTOCOL_OPTIONS:
            # building estimate duration message
            est_dur_msg = self.__msg_serializer(
                    'EstimateDurationRequest', 
                    {'protocol': self.SIMPLE_PROTON_PROTOCOL},
                    'Option',
                    {'name': 'Scan', 'value': f'{option}'}
                    )
            
            # for debugging reasons:
            self.logger.info(est_dur_msg.decode())
            
            # sending the message
            try:
                self._spinsolve_client.sendall(est_dur_msg)
            except Exception as E:
                self.logger.critical(f'some error occured: {E}')
        else:
            self.logger.debug('selected option is not valid')

        
#if __name__ == '__main__':
#    myss = myspinsolve()
#    myss.shim('CheckShim', reference_peak=1.94)