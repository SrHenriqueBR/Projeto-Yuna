#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "YunaSignals.h"
#include "YunaAvatarActor.generated.h"

class USceneComponent;
class USkeletalMeshComponent;

// Coloque um SkeletalMesh importado pelo VRM4U em AvatarMesh no editor.
// O ator apenas LÊ dados validados de Projeto-Yuna/data; não envia comandos.
UCLASS(Blueprintable)
class YUNAUNREAL_API AYunaAvatarActor : public AActor
{
    GENERATED_BODY()

public:
    AYunaAvatarActor();
    virtual void Tick(float DeltaSeconds) override;
    virtual void BeginPlay() override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Yuna|Avatar")
    TObjectPtr<USkeletalMeshComponent> AvatarMesh;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    FYunaSignals Signals;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName MouthMorphName = TEXT("A");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName BlinkMorphName = TEXT("Blink");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName HappyMorphName = TEXT("Joy");

    // Use este evento em um Blueprint filho para animar mãos, roupas, olhos etc.
    UFUNCTION(BlueprintImplementableEvent, Category="Yuna|Animation")
    void OnYunaSignalsChanged(const FYunaSignals& NewSignals);

private:
    UPROPERTY()
    TObjectPtr<USceneComponent> SceneRoot;

    double Elapsed = 0.0;
    float PollAccumulator = 0.f;
    double LastValidStateAt = -1000.0;
    float TargetMouth = 0.f;
    float DesiredEmotionIntensity = 0.f;
    FString DesiredPose = TEXT("idle");
    FString DesiredEmotion = TEXT("neutral");
    bool bDesiredSpeaking = false;

    bool ReadLocalState();
    void UpdateAnimation(float DeltaSeconds);
};
