using UnrealBuildTool;
using System.Collections.Generic;

public class YunaUnrealEditorTarget : TargetRules
{
    public YunaUnrealEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        ExtraModuleNames.Add("YunaUnreal");
    }
}
