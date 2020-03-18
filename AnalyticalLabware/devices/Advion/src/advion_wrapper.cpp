#define NULL nullptr

#include<AdvionCMS.h>

#include<AcquisitionManager.h>
#include<AcquisitionListener.h>

#include<Instrument.h>
#include<InstrumentController.h>

#include<USBInstrument.h>
#include<SimulatedInstrument.h>

#include <DataReader.h>
#include <new>

using namespace AdvionCMS;
using AdvionData::DataReader;
namespace D = AdvionData;

#define DLLEXPORT extern "C" __declspec(dllexport)

/*
 Instruments
 */
DLLEXPORT Instrument* usb_instrument() {
	return static_cast<Instrument *>(new USBInstrument());
}

DLLEXPORT Instrument* simulated_instrument(const char *folder) {
	return static_cast<Instrument *>(new SimulatedInstrument(folder));
}

DLLEXPORT void set_switch(Instrument *instrument, InstrumentSwitch swtch, bool value) {
	instrument->setInstrumentSwitchOn(swtch, value);
}

DLLEXPORT void ignore_remaining_pumpdown_time(Instrument *instrument) {
	instrument->ignoreRemainingPumpDownTime();
}

DLLEXPORT int get_pumpdown_remaining_seconds(Instrument *instrument) {
	return instrument->getPumpDownRemainingSeconds();
}

DLLEXPORT SourceType get_source(Instrument *instrument) {
	return instrument->getSourceType();
}

DLLEXPORT double get_number_readback(Instrument *instrument, NumberReadback id) {
	return instrument->getNumberReadback(id);
}

DLLEXPORT bool get_binary_readback(Instrument *instrument, BinaryReadback id) {
	return instrument->getBinaryReadback(id);
}

/*
AcquisitionManager
 */
DLLEXPORT ErrorCode start(const char *methodXML, const char *ionSourceXML, const char *tuneXML, const char *name, const char *folder) {
	return AcquisitionManager::start(methodXML, ionSourceXML, tuneXML, name, folder);
}

DLLEXPORT ErrorCode start_with_switching(const char *methodXML,
										 const char *ionSourceXML1, const char *ionSourceXML2,
										 const char *tuneXML1, const char *tuneXML2,
										 const char *name, const char *folder) {
	return AcquisitionManager::startWithSwitching(methodXML,
												  ionSourceXML1, ionSourceXML2,
												  tuneXML1, tuneXML2,
												  name, folder);
}

DLLEXPORT ErrorCode stop() {
	return AcquisitionManager::stop();
}

DLLEXPORT ErrorCode pause() {
	return AcquisitionManager::pause();
}

DLLEXPORT ErrorCode resume() {
	return AcquisitionManager::resume();
}

DLLEXPORT int extend(int seconds) {
	return AcquisitionManager::extend(seconds);
}

DLLEXPORT AcquisitionState get_state() {
	return AcquisitionManager::getState();
}

DLLEXPORT const char *get_current_folder() {
	return AcquisitionManager::getCurrentFolder();
}

DLLEXPORT int get_acquisition_bins_per_amu() {
	return AcquisitionManager::getAcquisitionBinsPerAMU();
}

DLLEXPORT ErrorCode set_acquisition_bins_per_amu(int bins_per_amu) {
	return AcquisitionManager::setAcquisitionBinsPerAMU(bins_per_amu);
}

DLLEXPORT int get_last_num_masses() {
	return AcquisitionManager::getLastNumMasses();
}

DLLEXPORT int get_max_num_masses() {
	return AcquisitionManager::getMaxNumMasses();
}

DLLEXPORT ErrorCode get_last_spectrum_masses(double *buff) {
	return AcquisitionManager::getLastSpectrumMasses(buff);
}

DLLEXPORT ErrorCode get_last_spectrum_intensities(double *buff) {
	return AcquisitionManager::getLastSpectrumIntensities(buff);
}

/*
 InstrumentController
 */
DLLEXPORT ErrorCode start_controller(Instrument *instrument) {
	return InstrumentController::startController(instrument);
}

DLLEXPORT ErrorCode stop_controller() {
	return InstrumentController::stopController();
}

DLLEXPORT bool can_vent() {
	return InstrumentController::canVent();
}

DLLEXPORT ErrorCode vent() {
	return InstrumentController::vent();
}

DLLEXPORT bool can_pump_down() {
	return InstrumentController::canPumpDown();
}

DLLEXPORT ErrorCode pump_down() {
	return InstrumentController::pumpDown();
}

DLLEXPORT InstrumentState get_instrument_state() {
	return InstrumentController::getState();
}

DLLEXPORT OperationMode get_operation_mode() {
	return InstrumentController::getOperationMode();
}

DLLEXPORT bool can_operate() {
	return InstrumentController::canOperate();
}

DLLEXPORT ErrorCode operate() {
	return InstrumentController::operate();
}

DLLEXPORT ErrorCode standby() {
	return InstrumentController::standby();
}

DLLEXPORT bool can_standby() {
	return InstrumentController::canStandby();
}

DLLEXPORT char *get_tune_parameters() {
	return InstrumentController::getTuneParameters();
}

DLLEXPORT ErrorCode set_tune_parameters(const char *tune_xml) {
	return InstrumentController::setTuneParameters(tune_xml);
}

DLLEXPORT char *get_ion_source_optimization() {
	return InstrumentController::getIonSourceOptimization();
}

DLLEXPORT ErrorCode set_ion_source_optimization(const char *ion_source_xml) {
	return InstrumentController::setIonSourceOptimization(ion_source_xml);
}

/*
 Data processing
 */
DLLEXPORT void* make_reader(const char* path, bool debugOutput = false, bool decodeSpectra = false) {
	DataReader *dr = new(std::nothrow) DataReader(path, debugOutput, decodeSpectra);
	return dr;
}

DLLEXPORT void free_reader(DataReader *dr) {
	delete dr;
}

DLLEXPORT D::ErrorCode get_delta_background_spectrum(DataReader *dr, float *intensities) {
	return dr->getDeltaBackgroundSpectrum(intensities);
}

DLLEXPORT D::ErrorCode get_delta_spectrum(DataReader *dr, int index, float *intensities) {
	return dr->getDeltaSpectrum(index, intensities);
}

DLLEXPORT D::ErrorCode get_spectrum(DataReader *dr, int index, float *intensities) {
	return dr->getSpectrum(index, intensities);
}

DLLEXPORT D::ErrorCode get_masses(DataReader *dr, float *masses) {
	return dr->getMasses(masses);
}

DLLEXPORT int num_masses(DataReader *dr) {
	return dr->getNumMasses();
}

DLLEXPORT int num_spectra(DataReader *dr) {
	return dr->getNumSpectra();
}

DLLEXPORT D::ErrorCode retention_times(DataReader *dr, float *times) {
	return dr->getRetentionTimes(times);
}

DLLEXPORT float get_TIC(DataReader *dr, int index) {
	return dr->getTIC(index);
}
