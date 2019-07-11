from os.path import join, isdir
from os import listdir
import os
import struct
import numpy as np
from scipy import sparse, signal
import matplotlib.pyplot as plt
from scipy.optimize import fmin, curve_fit
import socket
import time
import datetime
import shutil


def default_processing(s, solvent = 'dmso'):
    s.fft()
    s.gen_x_scale()
    s.phase(0, 0)
    if solvent.lower() == 'mecn':
        s.reference(1.96)
    elif solvent.lower() == 'dmso':
        s.reference(2.50)
    elif solvent.lower() == "cdcl3":
        s.reference(7.26)
    elif solvent.lower() == "dioxane":
        s.reference(3.60)
    elif solvent.lower() == 'methanol':
        s.reference(3.34)
#    s.normalize()
#    s.remove_solvent()
#    s.remove_satellites()
#    s.remove_water()
#    s.cut(0, 12)

    # s.show()


def getIPAddresses():
    from ctypes import Structure, windll, sizeof
    from ctypes import POINTER, byref
    from ctypes import c_ulong, c_uint, c_ubyte, c_char
    MAX_ADAPTER_DESCRIPTION_LENGTH = 128
    MAX_ADAPTER_NAME_LENGTH = 256
    MAX_ADAPTER_ADDRESS_LENGTH = 8

    class IP_ADDR_STRING(Structure):
        pass

    LP_IP_ADDR_STRING = POINTER(IP_ADDR_STRING)
    IP_ADDR_STRING._fields_ = [
        ("next", LP_IP_ADDR_STRING),
        ("ipAddress", c_char * 16),
        ("ipMask", c_char * 16),
        ("context", c_ulong)]

    class IP_ADAPTER_INFO(Structure):
        pass

    LP_IP_ADAPTER_INFO = POINTER(IP_ADAPTER_INFO)
    IP_ADAPTER_INFO._fields_ = [
        ("next", LP_IP_ADAPTER_INFO),
        ("comboIndex", c_ulong),
        ("adapterName", c_char * (MAX_ADAPTER_NAME_LENGTH + 4)),
        ("description", c_char * (MAX_ADAPTER_DESCRIPTION_LENGTH + 4)),
        ("addressLength", c_uint),
        ("address", c_ubyte * MAX_ADAPTER_ADDRESS_LENGTH),
        ("index", c_ulong),
        ("type", c_uint),
        ("dhcpEnabled", c_uint),
        ("currentIpAddress", LP_IP_ADDR_STRING),
        ("ipAddressList", IP_ADDR_STRING),
        ("gatewayList", IP_ADDR_STRING),
        ("dhcpServer", IP_ADDR_STRING),
        ("haveWins", c_uint),
        ("primaryWinsServer", IP_ADDR_STRING),
        ("secondaryWinsServer", IP_ADDR_STRING),
        ("leaseObtained", c_ulong),
        ("leaseExpires", c_ulong)]
    GetAdaptersInfo = windll.iphlpapi.GetAdaptersInfo
    GetAdaptersInfo.restype = c_ulong
    GetAdaptersInfo.argtypes = [LP_IP_ADAPTER_INFO, POINTER(c_ulong)]
    adapterList = (IP_ADAPTER_INFO * 10)()
    buflen = c_ulong(sizeof(adapterList))
    rc = GetAdaptersInfo(byref(adapterList[0]), byref(buflen))
    if rc == 0:
        for a in adapterList:
            adNode = a.ipAddressList
            while True:
                ipAddr = adNode.ipAddress
                if ipAddr:
                    yield ipAddr
                adNode = adNode.next
                if not adNode:
                    break


# class nmr():
#     def __init__(self, nmr_dir='C:\Projects\Data',
#                  spinsolve='C:\Users\Flow-NMR\AppData\Local\Magritek\Spinsolve\Spinsolve.exe',
#                  port=13000):
#         self.nmr_dir = nmr_dir
#         self.port = port
#         self.spinsolve = spinsolve
#
#     def abort(self):
#         host = '127.0.0.1'
#         for addr in getIPAddresses():
#             if addr != '0.0.0.0':
#                 host = addr
#                 break
#         print('connecting to nmr ', host, ':', self.port)
#
#         message = '<?xml version="1.0" encoding="UTF-8"?>\n'
#         message += '<Message>\n'
#         message += '<Abort/>\n'
#         message += '</Start>\n'
#         message += '</Message>\n'
#
#         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         s.connect((host, self.port))
#         time.sleep(0.1)
#         s.sendall(message.encode())
#         s.close()
#
#     def call_nmr(self, path):
#         from xml.etree import ElementTree
#
#         host = '127.0.0.1'
#         for addr in getIPAddresses():
#             if addr != '0.0.0.0':
#                 host = addr
#
#         # creating spinsolve process
#         os.system("taskkill /f /IM Spinsolve.exe")
#         os.system("start " + self.spinsolve)
#         time.sleep(10)
#
#         message = '<?xml version="1.0" encoding="UTF-8"?>\n'
#         message += '<Message>\n'
#         message += '<Start protocol="1D PROTON" >\n'
#         message += '<Option name="Scan" value="QuickScan" />\n'
#         message += '</Start>\n'
#         message += '</Message>\n'
#
#         for i in range(0, 5):
#             try:
#                 print('trying to connect to nmr ', host, ':', self.port)
#                 s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 s.connect((host, self.port))
#             except:
#                 continue
#
#             print
#             'conected to ', host, ':', self.port
#             time.sleep(1)
#             s.sendall(message.encode())
#             time.sleep(0.1)
#             s.settimeout(60)
#
#             ### waiting for response
#             try:
#                 response = s.recv(1024)
#                 s.close()
#                 xmlresp = ElementTree.fromstring(response)
#                 # If  NMR is busy try to send another command.
#                 if xmlresp.getchildren()[0].getchildren()[0].get('error') == 'Device is busy':
#                     print
#                     'Device is busy waiting for 60s'
#                     time.sleep(60)
#                     continue
#
#             except:
#                 s.close()
#             else:
#                 break
#
#         time.sleep(10)
#         os.system("taskkill /f /IM Spinsolve.exe")
#
#         xmlresp = ElementTree.fromstring(response)
#         print
#         response
#         if xmlresp.getchildren()[0].getchildren()[0].tag == 'Error':
#             print
#             'Spectrometer error'
#             if xmlresp.getchildren()[0].getchildren()[0].get('error')[0:22] == 'Unstable lock detected':
#                 print
#                 'You need to shim nmr'
#                 raise ValueError('You need to shim nmr')
#
#         if xmlresp.getchildren()[0].getchildren()[0].get('status') != 'Ready':
#             raise ValueError('Acquisition error')
#
#         year = str(datetime.date.today().year)
#         self.nmr_path = join(self.nmr_dir, year)
#         month = str(datetime.date.today().month)
#         if len(month) == 1:
#             month = '0' + month
#         self.nmr_path = join(self.nmr_path, month)
#         day = str(datetime.date.today().day)
#         if len(day) == 1:
#             day = '0' + day
#         self.nmr_path = join(self.nmr_path, day)
#         dirs = [join(self.nmr_path, d) for d in listdir(self.nmr_path) if isdir(join(self.nmr_path, d))]
#         nmr_dir = dirs[-1]
#         print
#         'last experimetn dir', nmr_dir
#         path = join(path, '1H')
#         try:
#             shutil.copytree(nmr_dir, path)
#         except WindowsError, e:
#             print
#             e
#
#     def check_shim(self):
#         from xml.etree import ElementTree
#
#         host = '127.0.0.1'
#         for addr in getIPAddresses():
#             if addr != '0.0.0.0':
#                 host = addr
#                 break
#
#         message = '<?xml version="1.0" encoding="UTF-8"?>\n'
#         message += '<Message>\n'
#         message += '<Start protocol="SHIM" >\n'
#         message += '<Option name="Shim" value="CheckShim" />\n'
#         message += '</Start>\n'
#         message += '</Message>\n'
#
#         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         s.connect((host, self.port))
#         time.sleep(0.1)
#         s.sendall(message.encode())
#         response = s.recv(1024)
#         print
#         response
#         xmlresp = ElementTree.fromstring(response)
#         print
#         xmlresp.getchildren()[0].getchildren()[0].tag
#
#     def quick_shim(self):
#         from xml.etree import ElementTree
#
#         host = '127.0.0.1'
#         for addr in getIPAddresses():
#             if addr != '0.0.0.0':
#                 host = addr
#                 break
#
#         message = '<?xml version="1.0" encoding="UTF-8"?>\n'
#         message += '<Message>\n'
#         message += '<Start protocol="SHIM" >\n'
#         message += '<Option name="Shim" value="QuickShim" />\n'
#         message += '</Start>\n'
#         message += '</Message>\n'
#
#         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         s.connect((host, self.port))
#         time.sleep(0.1)
#         s.sendall(message.encode())
#         response = s.recv(1024)
#         print
#         response
#         xmlresp = ElementTree.fromstring(response)
#         print
#         xmlresp.getchildren()[0].getchildren()[0].tag
#

class nmr_spectrum():
    def __init__(self, path=None, verbose=False, X_scale=[], spectrum=[]):
        # self.nmr_dir = nmr_dir
        self.verbose = verbose
        self.spectrum = spectrum
        self.X_scale = X_scale
        self.nmr_folder = path

        if path != None:
            # read spectrum parameters
            spectrum_parameters = open(join(path, 'acqu.par'), 'r')
            parameters = spectrum_parameters.readlines()
            self.param_dict = {}
            for param in parameters:
                self.param_dict[param.split('= ')[0].strip(' ')] = \
                    param.split('= ')[1].strip('\n')
            if self.verbose:
                print(self.param_dict)

            # open file with nmr data
            spectrum_path = join(path, 'data.1d')
            # open binary file with spectrum
            nmr_data = open(spectrum_path, mode='rb')
            # read first eight bytes
            spectrum = []
            # unpack the data
            while True:
                data = nmr_data.read(4)
                if not data:
                    break
                spectrum.append(struct.unpack('<f', data))
            # remove fisrt eight points and divide data into three parts
            lenght = int(len(spectrum[8:]) / 3)
            # print (type(spectrum))
            fid = spectrum[lenght + 8:]
            self.gamma = 1 / max(spectrum[8:lenght])[0]
            fid_real = []
            fid_img = []
            for i in range(int(len(fid) / 2)):
                fid_real.append(fid[2 * i][0])
                fid_img.append(fid[2 * i + 1][0])
            self.fid_complex = []
            for i in range(len(fid_real)):
                self.fid_complex.append(np.complex(fid_real[i], fid_img[i] * -1))

    def fft(self):
        self.spectrum = np.fft.fft(self.fid_complex,
                                   n=1 * len(self.fid_complex))
        self.spectrum = np.fft.fftshift(self.spectrum)
        self.spectrum_length = len(self.spectrum)

    def phase(self, phase0=0.0, phase1=0.0):
        phase0_rad = np.pi * phase0 / 180
        phase1_rad = np.pi * phase1 / 180

        phased_spectrum = []
        # phase spectrum
        for (i, point) in enumerate(self.spectrum):
            correction = i * phase1_rad / self.spectrum_length + phase0_rad
            real_part = np.cos(correction) * point.real - \
                        np.sin(correction) * point.imag
            imag_part = np.cos(correction) * point.imag - \
                        np.sin(correction) * point.real
            phased_spectrum.append(np.complex(real_part, imag_part))
        self.spectrum = phased_spectrum

    def show(self):
        plt.plot(self.X_scale, self.spectrum)
        plt.gca().invert_xaxis()
        # if hasattr(self, 'peaks'):
        # plt.plot([i[0] for i in self.peaks],
        # [i[1] for i in self.peaks], 'ro')
        plt.show()

    def integrate(self, low_ppm, high_ppm):
        peak = [self.spectrum[i].real for i, v in
                enumerate(self.X_scale) if (v > low_ppm and v < high_ppm)]
        return np.trapz(peak)

    def gen_x_scale(self):
        self.X_scale = []
        for (i, point) in enumerate(self.spectrum):
            x = (i * 5000. / self.spectrum_length +
                 float(self.param_dict['lowestFrequency'])) / \
                float(self.param_dict['b1Freq'])
            self.X_scale.append(x)

    def cut(self, low_ppm=5, high_ppm=12):
        self.spectrum = [self.spectrum[i] for (i, p) in
                         enumerate(self.X_scale) if (p > low_ppm) and (p < high_ppm)]
        self.X_scale = [i for i in self.X_scale if (i > low_ppm) and (i < high_ppm)]

    def autophase(self):
        def entropy(phase):
            def penalty_function(Ri):
                if Ri >= 0:
                    return 0
                else:
                    return np.square(Ri)

            phase0_rad = np.pi * phase[0] / 180
            phase1_rad = np.pi * phase[1] / 180
            real_spectrum = [i.real for i in self.spectrum]
            p_real_spectrum = []
            for (i, ri) in enumerate(self.spectrum):
                correction = phase0_rad + i * phase1_rad / self.spectrum_length
                ci = ri.real * np.cos(correction) - ri.imag * np.sin(correction)
                p_real_spectrum.append(ci)

            penalty = 1e-14 * np.sum([penalty_function(i) for i in p_real_spectrum])
            first_derivative = np.gradient(p_real_spectrum)
            ssum = np.sum(np.absolute(first_derivative))
            prob = [np.absolute(i) / ssum for i in first_derivative]
            entropy = np.sum([-p * np.log(p) for p in prob])

            # print entropy, penalty
            return entropy + penalty

        new_phase = fmin(entropy, [0, 0], )
        self.phase(new_phase[0], new_phase[1])

    def baseline_als(self, lam, p, niter=10):
        self.spectrum = [i.real for i in self.spectrum]
        L = len(self.spectrum)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = sparse.linalg.spsolve(Z, w * self.spectrum)
            w = p * (self.spectrum > z) + (1 - p) * (self.spectrum < z)
        self.spectrum = self.spectrum - z

    def smooth(self, lam, p, niter=10):
        self.spectrum = [i.real for i in self.spectrum]
        L = len(self.spectrum)
        D = sparse.csc_matrix(np.diff(np.eye(L), 2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = sparse.linalg.spsolve(Z, w * self.spectrum)
            w = p * (self.spectrum > z) + (1 - p) * (self.spectrum < z)
        self.spectrum = z
        plt.plot(self.X_scale, self.spectrum)
        plt.plot(self.X_scale, z)
        plt.show()
        self.spectrum = z

    def remove_solvent(self):
        dmso_ind = []

        for i in self.X_scale:
            if i > 2.10 and i < 2.90:
                dmso_ind.append(self.X_scale.index(i))
        for i in dmso_ind:
            self.spectrum[i] = 0.000

    def remove_satellites(self):
        s = []

        for i in self.X_scale:
            if (i > 3.5 and i < 3.7) or (i > 1.3 and i < 1.5):
                s.append(self.X_scale.index(i))
        for i in s:
            self.spectrum[i] = 0.000

    def remove_water(self):
        w = []
        for i in self.X_scale:
            if i > 3.24 and i < 3.6:
                w.append(self.X_scale.index(i))
        for i in w:
            self.spectrum[i] = 0.000



    def find_peaks(self, thresh=0.3, min_dist=0.5):
        thresh *= (np.max(self.spectrum) - np.min(self.spectrum))
        smooth = signal.savgol_filter(self.spectrum, 3, 2)
        dy = np.diff(smooth)

        peaks = np.where((np.hstack([dy, 0.]) < 0) &
                         (np.hstack([0., dy]) > 0) &
                         (self.spectrum > thresh))[0]

        # peaks = signal.find_peaks_cwt(self.spectrum,
        # np.arange(70,90), noise_perc = 20)
        self.spectrum = np.real(self.spectrum)

        self.peaks = [[self.X_scale[i], self.spectrum[i]] for i in peaks]
        # print self.peaks
        # remove peaks to close to each other
        idx_to_remove = []
        for i, p in enumerate(self.peaks):
            if i not in idx_to_remove:
                for j in range(i + 1, len(self.peaks)):
                    if abs(self.peaks[i][0] - self.peaks[j][0]) < min_dist:
                        if self.peaks[j][1] - self.peaks[i][1] > 0:
                            if i not in idx_to_remove:
                                idx_to_remove.append(i)
                        else:
                            if j not in idx_to_remove:
                                idx_to_remove.append(j)

        sorted_peaks = []
        for i, p in enumerate(self.peaks):
            if i not in idx_to_remove:
                sorted_peaks.append(self.peaks[i])
        self.peaks = sorted_peaks

        #        plt.plot(self.X_scale, self.spectrum)
        #        for p in self.peaks:
        #            params = self.fit_lorentzian(p[0], p[1])
        #            fitted = [self.lorentzian(i, params[0],
        #            params[1], params[2]) for i in self.X_scale]
        #            plt.plot(self.X_scale, fitted)
        #        plt.show()
        return self.peaks

    def lorentzian(self, p, p0, ampl, w):
        x = (p0 - p) / (w / 2)
        return ampl / (1 + x * x)

    def fit_lorentzian(self, x, y):
        initial = [x, y, 0.07]
        params, pcov = curve_fit(self.lorentzian, self.X_scale,
                                 self.spectrum, initial, maxfev=5000)
        return params

    def autointegrate(self, lowb, highb, show=False):
        spectrum = self.spectrum[:]
        X_scale = self.X_scale[:]
        self.cut(lowb, highb)
        # self.smooth(1e1, .9)
        # find peak having the highest intensity
        peak = sorted(self.find_peaks(thresh=0.2), key=lambda x: x[1], reverse=True)[0]
        fit_params = self.fit_lorentzian(peak[0], peak[1])
        fitted = [self.lorentzian(i, fit_params[0], fit_params[1], fit_params[2]) for i in self.X_scale]
        area = np.trapz(fitted)
        # if peak has a half width larger then 0.2 ppm return 0
        # fitting process probably failed
        if show == True:
            plt.plot(self.X_scale, self.spectrum)
            plt.plot(self.X_scale, fitted)
            plt.show()

        self.spectrum = spectrum[:]
        self.X_scale = X_scale[:]

        if fit_params[2] > 0.2:
            return 0
        else:
            return area

    def normalize(self):
        self.spectrum = [i.real for i in self.spectrum]
        max_intensity = sorted(self.spectrum)[-1]
        self.spectrum = [i / max_intensity for i in self.spectrum]

    def __sub__(self, other):
        from operator import sub
        new_spectrum = map(sub, self.spectrum, other.spectrum)
        return nmr_spectrum(X_scale=self.X_scale, spectrum=new_spectrum)

    def __add__(self, other):
        from operator import add
        new_spectrum = map(add, self.spectrum, other.spectrum)
        return nmr_spectrum(X_scale=self.X_scale, spectrum=new_spectrum)

    def __mul__(self, other):
        new_spectrum = [i * other for i in self.spectrum]
        return nmr_spectrum(X_scale=self.X_scale, spectrum=new_spectrum)

    def __rmul__(self, other):
        new_spectrum = [i * other for i in self.spectrum]
        return nmr_spectrum(X_scale=self.X_scale, spectrum=new_spectrum)

    def reference(self, solvent_shift):
        diff = solvent_shift - self.find_peaks(thresh=0.5)[0][0]
        self.X_scale = [i + diff for i in self.X_scale]


if __name__ == '__main__':


    spectrum = nmr_spectrum('C:\\20190121170920')
    default_processing(spectrum)
    # spectrum.autointegrate()

    # spectrum.show()
    # nmr1 = nmr()
    # nmr1.call_nmr('C:\Users\Flow-NMR\Desktop\\rxns')

##    def process(s):
##        s.fft()
##        s.gen_x_scale()
##        s.cut(0,5)
##        s.phase(30,0)
##        s.reference(1.60)
##        s.normalize()
##
##    s1 = nmr_spectrum('C:\Users\Group.Taketsuru\Desktop\\rxns\\methylacetoacetate')
##    process(s1)
##    s1.show()
##    s2 = nmr_spectrum('C:\Users\Group.Taketsuru\Desktop\\rxns\\benzylamine')
##    process(s2)
##    s3 = nmr_spectrum('C:\Users\Group.Taketsuru\Desktop\\rxns\\benzylamine_methylacetoacetate')
##    process(s3)
##
##    def fitf(params):
##        s4 = params[0]*(params[1]*s1+params[2]*s2)
##        s5 = s4-s3
##        return sum([i*i for i in s5.spectrum])
##
##    params = fmin(fitf, [0.5, 1, 1])
##    #params = [0.5, 1, 1]
##
##    s4 = params[0]*(params[1]*s1+params[2]*s2)
##
##    #plt.plot(s1.X_scale, s1.spectrum)
##    #plt.plot(s2.X_scale, s2.spectrum)
##    plt.plot(s3.X_scale, s3.spectrum)
##    plt.plot(s4.X_scale, s4.spectrum)
##    plt.show()


