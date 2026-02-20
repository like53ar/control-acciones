Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Cerrar instancias previas para limpiar los puertos (usando taskkill nativo de Windows para evitar PowerShell)
WshShell.Run "cmd.exe /c taskkill /F /IM node.exe /T 2>nul", 0, True
WshShell.Run "cmd.exe /c taskkill /F /IM python.exe /T 2>nul", 0, True
WshShell.Run "cmd.exe /c taskkill /F /IM uvicorn.exe /T 2>nul", 0, True

' Iniciar Backend oculto
WshShell.Run "cmd.exe /c ""cd /d """ & scriptDir & "\backend"" && node server.js""", 0, False

' Iniciar Frontend oculto
WshShell.Run "cmd.exe /c ""cd /d """ & scriptDir & "\frontend"" && npm start""", 0, False

' Mostrar pantalla de carga moderna (Splash Screen basada en HTA)
WshShell.Run "mshta.exe """ & scriptDir & "\splash.hta""", 1, True

' Abrir el navegador en el puerto de Angular
WshShell.Run "http://localhost:4200"
