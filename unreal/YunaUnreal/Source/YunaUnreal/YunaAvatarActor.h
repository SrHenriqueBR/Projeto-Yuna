#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "YunaSignals.h"
#include "YunaAvatarActor.generated.h"

class USceneComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UPoseableMeshComponent;

// Lê apenas os estados visuais da Yuna. NUNCA abre microfone, câmera, rede
// ou executa comandos vindos do Python.
UCLASS(Blueprintable)
class YUNAUNREAL_API AYunaAvatarActor : public AActor
{
    GENERATED_BODY()

public:
    AYunaAvatarActor();
    virtual void Tick(float DeltaSeconds) override;
    virtual void BeginPlay() override;

    // Coloque aqui seu SkeletalMesh anime importado com rig.
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Yuna|Avatar")
    TObjectPtr<USkeletalMeshComponent> AvatarMesh;

    // Preview direto: move ossos sem criar um Animation Blueprint manual.
    // Limitação da UPoseableMeshComponent: morph targets e simulações de
    // cabelo do SkeletalMesh original não são reproduzidos neste modo.
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Yuna|Avatar")
    TObjectPtr<UPoseableMeshComponent> DirectBoneMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Preview")
    bool bDirectBonePreview = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Preview")
    bool bReducedMotion = false;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    FYunaSignals Signals;

    // Modo SkeletalMesh/Animation Blueprint: morph targets de rosto.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName MouthMorphName = TEXT("A");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName BlinkMorphName = TEXT("Blink");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName LeftBlinkMorphName = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName RightBlinkMorphName = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|MorphTargets")
    FName HappyMorphName = TEXT("Joy");

    // Opcional: se não definidos, procuram-se nomes comuns VRM/VRoid.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName HeadBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName ChestBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName LeftArmBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName RightArmBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName LeftLegBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName RightLegBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName LeftEyeBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName RightEyeBone = NAME_None;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Yuna|Bones")
    FName HairBone = NAME_None;

    UFUNCTION(BlueprintImplementableEvent, Category="Yuna|Animation")
    void OnYunaSignalsChanged(const FYunaSignals& NewSignals);

private:
    UPROPERTY()
    TObjectPtr<USceneComponent> SceneRoot;

    double Elapsed = 0.0;
    float PollAccumulator = 0.f;
    double LastValidStateAt = -1000.0;
    double PoseExpiresAt = 0.0;
    int64 LastGestureSeq = -1;
    FString LastSession;
    FTransform BaseAvatarMeshTransform = FTransform::Identity;
    float DesiredEmotionIntensity = 0.f;
    float TargetMouth = 0.f;
    FString DesiredPose = TEXT("idle");
    FString DesiredEmotion = TEXT("neutral");
    bool bDesiredSpeaking = false;
    bool bHasAmplitude = false;

    USkeletalMesh* CachedDirectAsset = nullptr;
    FName ResolvedHead, ResolvedChest, ResolvedLeftArm, ResolvedRightArm;
    FName ResolvedLeftLeg, ResolvedRightLeg, ResolvedLeftEye, ResolvedRightEye, ResolvedHair;

    bool ReadLocalState();
    void UpdateAnimation(float DeltaSeconds);
    bool SyncDirectBonePreview();
    FName FindBone(const FName& Preferred, const TArray<FName>& Candidates) const;
    void ResolveBones();
    void RotateBone(const FName& Bone, const FRotator& Delta) const;
};
