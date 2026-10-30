using UnrealBuildTool;
using System.Collections.Generic;

public class YunaUnrealTarget : TargetRules
{
    public YunaUnrealTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        ExtraModuleNames.Add("YunaUnreal");
    }
}
