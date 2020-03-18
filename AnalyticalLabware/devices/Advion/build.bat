set INCLUDE_DIR="..\AdvionAPI.6.0.11.3.VS10\include"
set LIB_DIR="..\AdvionAPI.6.0.11.3.VS10\Release"
set OUTPUT="advion_wrapper/advion_wrapper.dll"

cl /LD /Fe%OUTPUT% /I %INCLUDE_DIR% %LIB_DIR%\*.lib src/advion_wrapper.cpp