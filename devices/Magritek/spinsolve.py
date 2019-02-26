#!/usr/bin/env python
# coding: utf-8

import threading, socket, time, logging
import xml.etree.ElementTree as ET

#from queue import Queue
from io import BytesIO

logging.basicConfig(level=logging.INFO)

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
                self.logger.error(f'connection error: {E}')
                time.sleep(60)
                continue
        
        # spawning and starting the thread for receiving messages
        self._receiving_thread = threading.Thread(target=self._receive, name='Spinsolve data receiving thread', daemon=True)
        self._receiving_thread.start()
        
        # connection event
        # small remark here:
        # even though the nrm software prevents multiple attempts to perform the measurement and sends the error
        # message in that case, to avoind confusion during the response parsing the Event is introduced to block
        # the Start protocol messages until the current is done. See the details in __msg_parser() method
        self._connection_event = threading.Event()
        self._connection_event.set()
        
        # selected documented commands for easier maintanance
        self.SIMPLE_PROTON_PROTOCOL = '1D PROTON'
        self.SIMPLE_PROTON_PROTOCOL_OPTIONS = ('QuickScan', 'StandardScan', 'PowerScan')
        self.SAMPLE_SHIM_PROTOCOL = 'SHIM 1H SAMPLE'
        self.SAMPLE_SHIM_PROTOCOL_OPTIONS = ('CheckShim',
                                             'LockAndCalibrateOnly',
                                             'QuickShim1',
                                             'QuickShim2',
                                             'QuickShimAll',
                                             'PowerShim')
        self.CHECK_SHIM_REQUESTS = ('CheckShimRequest', 'QuickShimRequest', 'PowerShimRequest')
        # USER_FOLDER_TYPES specifies where the obtained spectrums will be saved:
        # "UserFolder" will save the data in the folder provided by nmr_path attribute
        # "TimeStamp" will save data in new folders as (yyyymmddhhmmss) in nmr_path folder
        # "TimeStampTree" will save the data in the set of timestamped folders as yyyy\mm\dd\hhmmss
        self.USER_FOLDER_TYPES = ('UserFolder',
                                  'TimeStamp',
                                  'TimeStampTree')
        
        self._self_check()
        self.user_folder()
    
    def __del__(self):
        '''
        Method for removing the class instance
        '''        
        
        # closing connection
        self._spinsolve_client.close()
        self.logger.info('connection closed')
        
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
            get_return (bool): will return the parameter if True
        '''
        
        # checking for the self-check response
        if 'Hardware' in tag:
            # getting the main element from the data_root
            main_element = data_root.find(f'.//{tag}')
            
            # looking for connection to the instrument
            connected_tag = main_element.find('.//ConnectedToHardware').text
            if connected_tag == 'false':
                self.logger.critical('The NMR instrument is not connected, try to reconnect it and run _self_check method again')
                return
            
            # looking for the software version
            software_tag = main_element.find('.//SpinsolveSoftware').text
            
            # looking for the instrument model
            try:
                spinsolve_tag = main_element.find('.//SpinsolveType').text
            except:
                spinsolve_tag = '"No instrument"'
            
            # logging the acquired information
            self.logger.info(f'The {spinsolve_tag} NMR instrument is successfully connected')
            self.logger.info(f'Running under Spinsolve software version {software_tag}')
            if software_tag[:4] != '1.13':
                self.logger.warning('Current software version {} was not tested, use at your own risk'.format(software_tag))
            return True
        
        # check for the check_shim response
        elif 'ShimResponse' in tag:
            # getting the main element from the root msg
            main_element = data_root.find(f'.//{tag}')
            
            # lookign for errors
            error_text = main_element.get('error')
            
            if error_text:
                self.logger.critical(f'shimming error: {error_text}')
            
            # logging the shimming results
            self.logger.info('shimming results:')
            for child in main_element:
                self.logger.info(f'{child.tag} - {child.text}')
            
            # obtaining shimming parameters
            line_width = round(float(main_element.find('.//LineWidth').text), 2)
            base_width = round(float(main_element.find('.//BaseWidth').text), 2)
            system_ready = main_element.find('.//SystemIsReady').text
            
            # checking parameters validity
            if line_width > 1.1:
                self.logger.critical('line width is too high, please use shim() method to perform the shimming procedure')
            if base_width > 40:
                self.logger.critical('base width is too high, please use shim() method to perform the shimming procedure')
            if system_ready != 'true':
                self.logger.critical('System is not ready, please use shim() method to perform the shimming procedure')
            else:
                return True
        
        elif 'Status' in tag:
            # acquiring the lock to block the input in case the protocol is already performing
            #self._connection_lock.acquire()
            
            # getting the main element
            main_element = data_root.find(f'.//{tag}')
            
            # obtaining valuable info
            state_tag = main_element.find('.//').tag
            state_elem = main_element.find(f'.//{state_tag}')
            protocol_attrib = state_elem.get('protocol')
            status_attrib = state_elem.get('status')
            percentage_attrib = state_elem.get('percentage')
            seconds_remaining_attrib = state_elem.get('secondsRemaining')
            
            # logging the data
            if state_tag == 'State':
                # resetting the event to False to block the incomming msg
                self._connection_event.clear()
                self.logger.info(f'{status_attrib} the {protocol_attrib} protocol')
                if status_attrib == 'Ready':
                    # when device is ready, setting the event to True for the next protocol to be executed
                    self._connection_event.set()
                    data_folder = state_elem.get('dataFolder')
                    self.logger.info(f'the protocol {protocol_attrib} is complete, the nmr is saved in {data_folder}')
                    return data_folder
            
            if state_tag == 'Progress':
                self.logger.info(f'the protocol {protocol_attrib} is performed, {percentage_attrib}% completed, {seconds_remaining_attrib} seconds remain') 
        
        # TODO parse every type of responses
        else:
            pass
    
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
                self.logger.debug('message received:\n' + data.decode())
                
                # creating bytes object for future parsing
                data_obj = BytesIO(data)
                                
                try:
                    # parsing the obtained message
                    data_tree = ET.parse(data_obj)
                    data_root = data_tree.getroot()
                    
                    # getting the main element tag
                    # looking for all children elements and writing the tag of the first obtained
                    data_tag = data_root.find('.//').tag
                    
                    # calling parser for valuable information logging
                    reply_message = self.__msg_parser(data_root, data_tag)
                    self.last_reply = reply_message
                    
                except Exception as exc:
                    # workaround the parsing errors
                    # sometimes server sends invalid XML messages with several XML roots
                    # that causes the error in parsing process
                    # in this case the message will be displayed in raw format
                    self.logger.error(f'parsing error: {exc}')
                    self.logger.debug('raw message:\n', data.decode())
                    continue
                
            except Exception as exc:
                # in case connection problems
                self.logger.error(exc)
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
            self.logger.error(f'some error occured: {E}')
    
    def proton(self, option='QuickScan'):
        '''
        Method for running the simple 1D proton experiment
        
        Args:
            option (str): scan type for the 1D PROTON protocol aviable from SIMPLE_PROTON_PROTOCOL_OPTIONS
        '''
        
        # validating provided option
        if option not in self.SIMPLE_PROTON_PROTOCOL_OPTIONS:
            self.logger.error('please select one of the following options: {}'.format(self.SIMPLE_PROTON_PROTOCOL_OPTIONS))
            return
        
        # building 1D PROTON protocol message
        proton_msg = self.__msg_serializer(
                'Start', 
                {'protocol': self.SIMPLE_PROTON_PROTOCOL},
                'Option',
                {'name': 'Scan', 'value': f'{option}'}
                )
        
        # for debugging reasons:
        self.logger.debug('message constructed:\n' + proton_msg.decode())
        
        # sending the message
        try:
            # waiting for the event to be set to prevent multiple outcomming messages
            self._connection_event.wait()
            self._spinsolve_client.sendall(proton_msg)
            self.logger.info(f'should start the {option} 1D proton nmr experiment')
        except Exception as E:
            self.logger.error(f'some error occured: {E}')
    
    def shim(self, request='CheckShimRequest'):
        '''
        Method for shimming the instrument to the standard solution (1:9 H20:D2O mixture, correspond to 4.74 ppm).
        Use calibrate method to calibrate frquency of the largest peak to ppm value of the solvent you use
        
        Args:
            request (str): shimming type, available from CHECK_SHIM_REQUESTS
        '''
        
        # validating provided attribute
        if request not in self.CHECK_SHIM_REQUESTS:
            self.logger.error('please select one of the following options: {}'.format(self.CHECK_SHIM_REQUESTS))
            return
        
        # buidling the message
        check_shim_msg = self.__msg_serializer(request)
        
        try:
            self._connection_event.wait()
            self._spinsolve_client.sendall(check_shim_msg)
        except Exception as E:
            self.logger.error(f'some error occured: {E}')
        
        
    def calibrate(self, reference_peak, option='LockAndCalibrateOnly'):
        '''
        Method for shimming the instrument to the provided reference peak
        
        Args:
            reference_peak (float): largest peak of the supplied sample
                used for the calibration of the ppm scale during shimming
            option (str): shimming type, available from SAMPLE_SHIM_PROTOCOL_OPTIONS
        '''
        # validating the reference peak value
        try:
            reference_peak = round(reference_peak, 2)
        except:
            self.logger.error('reference peak must be float')
            return
        
        # validating the option
        if option not in self.SAMPLE_SHIM_PROTOCOL_OPTIONS:
            self.logger.warning('please select one of the following options: {}'.format(self.SAMPLE_SHIM_PROTOCOL_OPTIONS))
            return
            
        # building shimming protocol message
        shimming_msg = self.__msg_serializer('Start', 
                                             {'protocol': self.SAMPLE_SHIM_PROTOCOL},
                                             'Option',
                                             {'name': 'SampleReference', 'value': f'{reference_peak}'},
                                             {'name': 'Shim', 'value': f'{option}'}
                                             )
        # for debugging reasons
        self.logger.debug('message sent:\n' + shimming_msg.decode())
        
        # sending the message
        try:
            self._connection_event.wait()
            self._spinsolve_client.sendall(shimming_msg)
            self.logger.info(f'should start the {option} shimming procedure, calibrating for {reference_peak} peak')
        except Exception as E:
            self.logger.error(f'some error occured: {E}')
        
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
            
            self.logger.debug('message sent:\n' + message_solvent.decode())
            self.logger.debug('message sent:\n' + message_sample.decode())
            
            try:
                self._spinsolve_client.sendall(message_solvent)
                self._spinsolve_client.sendall(message_sample)
            except Exception as E:
                self.logger.error(f'some error occured:{E}')
        except TypeError:
            self.logger.error('the method must be called with keyword arguments')

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
        # validating the given parameter
        if data_folder_type not in self.USER_FOLDER_TYPES:
            self.logger.warning('please select one of the following options: {}'.format(self.USER_FOLDER_TYPES))
            return
        
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
        
        self.logger.debug('message sent:\n' + message.decode())
        try:
            self._spinsolve_client.sendall(message)
        except Exception as E:
            self.logger.error(f'some error occured:{E}')

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
            self.logger.debug('message sent:\n' + est_dur_msg.decode())
            
            # sending the message
            try:
                self._spinsolve_client.sendall(est_dur_msg)
            except Exception as E:
                self.logger.error(f'some error occured: {E}')
        else:
            self.logger.error('selected option is not valid')
            
    def custom_msg(self, *args):
        my_msg = self.__msg_serializer(*args)
        self.logger.info('custom msg:\n' + my_msg.decode())
        try:
            self._connection_event.wait()
            self._spinsolve_client.sendall(my_msg)
        except:
            self.logger.error('error')
            pass

        
#if __name__ == '__main__':
#    myss = myspinsolve()
#    myss.shim('CheckShim', reference_peak=1.94)