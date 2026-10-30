#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "YunaSignals.h"
#include "YunaAnimInstance.generated.h"

// Crie um Animation Blueprint derivado desta classe e use Signals no AnimGraph.
// O projeto não distribui um modelo/rig VRM de terceiros.
UCLASS(Blueprintable)
class YUNAUNREAL_API UYunaAnimInstance : public UAnimInstance
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Animation")
    FYunaSignals Signals;
};
