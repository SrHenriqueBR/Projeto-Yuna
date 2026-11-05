#ifndef YunaVersion
  #define YunaVersion "0.51.1"
#endif
[Setup]
AppId={{0D5316AD-C9A6-4671-80DF-8BDF578E291A}
AppName=Yuna
AppVersion={#YunaVersion}
AppPublisher=Projeto Yuna - Kaizen
AppPublisherURL=https://github.com/SrHenriqueBR/Projeto-Yuna
AppSupportURL=https://github.com/SrHenriqueBR/Projeto-Yuna/issues
DefaultDirName={localappdata}\Programs\Yuna
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
AppMutex=Local\ProjetoYuna.App
UninstallDisplayIcon={app}\Yuna.exe
OutputDir=..\dist
OutputBaseFilename=Yuna-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho Yuna na Area de Trabalho"; Flags: checkedonce
Name: "startup"; Description: "Iniciar Yuna na bandeja ao entrar no Windows"; Flags: unchecked

[Files]
Source: "..\build\Yuna\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "app\data\*,*\__pycache__\*,*.pyc"

[Icons]
Name: "{userprograms}\Yuna.app"; Filename: "{app}\Yuna.exe"; Parameters: "--compact"; WorkingDir: "{app}\app"
Name: "{userdesktop}\Yuna.app"; Filename: "{app}\Yuna.exe"; Parameters: "--compact"; WorkingDir: "{app}\app"; Tasks: desktopicon
Name: "{userstartup}\Yuna.app"; Filename: "{app}\Yuna.exe"; Parameters: "--background"; WorkingDir: "{app}\app"; Tasks: startup

[Run]
Filename: "{app}\Yuna.exe"; Parameters: "--compact"; Description: "Abrir a Yuna"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userstartup}\Yuna.app.lnk"

[Code]
var
  ImportPage: TInputDirWizardPage;

procedure InitializeWizard();
begin
  ImportPage := CreateInputDirPage(wpSelectDir,
    'Ja usava a Yuna?', 'Copiar as memorias de uma pasta antiga (opcional)',
    'Feche a Yuna antiga. Selecione a pasta que contem data. A origem sera preservada. ' +
    'Se esta instalacao ja tiver memorias, elas nao serao substituidas. Deixe vazio para continuar.', False, '');
  ImportPage.Add('Pasta anterior do Projeto Yuna:');
  ImportPage.Values[0] := ExpandConstant('{param:YUNAMIGRATE|}');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = ImportPage.ID) and (ImportPage.Values[0] <> '') then
    if not DirExists(AddBackslash(ImportPage.Values[0]) + 'data') then begin
      MsgBox('Escolha a pasta do projeto que contem a pasta data.', mbError, MB_OK);
      Result := False;
    end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Arguments: String;
begin
  if (CurStep = ssPostInstall) and (ImportPage.Values[0] <> '') then begin
    Arguments := '-X utf8 "' + ExpandConstant('{app}\app\app_maintenance.py') +
      '" --import-data "' + AddBackslash(ImportPage.Values[0]) + '."';
    if not Exec(ExpandConstant('{app}\runtime\python.exe'), Arguments,
      ExpandConstant('{app}\app'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      ResultCode := 1;
    if ResultCode <> 0 then begin
      Log('YUNA_IMPORT_FAILED: memorias existentes/origem preservadas.');
      if not WizardSilent then
        MsgBox('O aplicativo foi instalado, mas a importacao nao foi concluida. ' +
          'Nenhuma memoria anterior foi sobrescrita. Se ja havia dados na instalacao, eles foram mantidos.', mbInformation, MB_OK);
    end else
      Log('YUNA_IMPORT_OK');
  end;
end;
