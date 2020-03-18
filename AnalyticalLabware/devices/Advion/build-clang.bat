set INCLUDE_DIR="../AdvionAPI.6.0.11.3.VS10/include"
set LIB_DIR="../AdvionAPI.6.0.11.3.VS10/Release"

clang -shared -o advion_wrapper/advion_wrapper.dll -m32 -std=c++14 -fms-extensions -I %INCLUDE_DIR% -L %LIB_DIR% -l AdvionCMS.lib src/advion_wrapper.cpp