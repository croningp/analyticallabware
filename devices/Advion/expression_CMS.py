# coding=utf-8
# !/usr/bin/env python
"""
"expression_CMS" -- API for Advion expression CMS mass spectrometer
====================================================================================

.. module:: expression_CMS
   :platform: Windows
   :synopsis: Advion expression CMS mass spectrometer.
   :license: BSD 3-clause
.. moduleauthor:: S. Hessam M. Mehr <Hessam.Mehr@chem.gla.ac.uk>
.. moduleauthor:: Jaroslaw Granda <Jaroslaw.Granda@chem.gla.ac.uk>

(c) 2018 The Cronin Group, University of Glasgow
"""

import logging

from advion import (AcquisitionManager, AcquisitionState, ErrorCode,
                    InstrumentController, InstrumentState, get_Instrument)
from os.path import dirname, join
from time import sleep

class ExpressionCMS:
    def __init__(self, ion_source='positiveAPCI.ion', method='default.method', tune='currentcalibESIpositive102016.tune'):
        filedir = join(dirname(__file__), 'files')
        self.ion_source = open(join(filedir, ion_source))
        self.method = open(join(filedir, method))
        self.tune = open(join(filedir, tune))
        self.controller = InstrumentController
        self.acqmgr = AcquisitionManager

    def __enter__(self):
        logging.info(f'Entering {self.__class__.__name__}')
        # Initialiaze mass spec controller
        err = self.controller.startController()
        if err != ErrorCode.CMS_OK:
            raise ValueError(f'Cannot initialize controller (got {err})')
        # Check if mass spec can operate
        while not self.controller.canOperate():
            logging.info('Waiting for ms')
            sleep(1)
        # Put mass spec into operate mode
        self.controller.operate()
        return self

    def measure_ms(self, name, path):
        logging.info(f'Acquiring {name} => {path}')
        err = self.acqmgr.start(self.method, self.ion_source, self.tune, name, path)
        if err != ErrorCode.CMS_OK:
            raise ValueError(f'Cannot measure (got {err})')
        logging.info('Waiting for ms to finish acquisition')
        sleep(1)
        logging.info(self.acqmgr.getState())
        while self.acqmgr.getState() == AcquisitionState.Underway:
            sleep(1)
        sleep(2)
        logging.info(self.acqmgr.isFinalizingData())
        logging.info(AcquisitionManager.getState())
        logging.info(f'Finished acquisition {name} => {path}')

    def isAcquisitionUnderway(self):
        return self.acqmgr.getState() == AcquisitionState.Underway

    def __exit__(self, errortype, value, traceback):
        logging.info(f'Exiting {self.__class__.__name__}')
        #check if ms can be put into standby mode
        while not self.controller.canStandby():
            sleep(0.1)
        #puts ms into standby mode
        self.controller.standby()
        #stop mscontroller
        self.controller.stopController()

if __name__ == '__main__':
    # testing code
    pass