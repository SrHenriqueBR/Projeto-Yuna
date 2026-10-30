#include "YunaAvatarActor.h"

#include "YunaAnimInstance.h"
#include "YunaMotion.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "HAL/FileManager.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
constexpr int64 MaxStateBytes = 2048;
constexpr float PollPeriod = 0.10f;
constexpr double StaleAfterSeconds = 2.5;

bool IsAllowedPose(const FString& Value)
{
    static const TSet<FString> Poses = {
        TEXT("idle"), TEXT("happy"), TEXT("curious"), TEXT("surprised"),
        TEXT("shy"), TEXT("wave"), TEXT("talk"), TEXT("wink"), TEXT("laugh"),
        TEXT("sit"), TEXT("walk"), TEXT("sleepy"), TEXT("angry"), TEXT("pose")
    };
    return Poses.Contains(Value);
}
bool IsAllowedEmotion(const FString& Value)
{
    static const TSet<FString> Emotions = {
        TEXT("neutral"), TEXT("happy"), TEXT("shy"),
        TEXT("sad"), TEXT("surprised"), TEXT("annoyed")
    };
    return Emotions.Contains(Value);
}
YunaMotion::EPose DecodePose(const FString& Pose)
{
    using P = YunaMotion::EPose;
    if (Pose == TEXT("happy")) return P::Happy;
    if (Pose == TEXT("curious")) return P::Curious;
    if (Pose == TEXT("surprised")) return P::Surprised;
    if (Pose == TEXT("shy")) return P::Shy;
    if (Pose == TEXT("wave")) return P::Wave;
    if (Pose == TEXT("talk")) return P::Talk;
    if (Pose == TEXT("wink")) return P::Wink;
    if (Pose == TEXT("laugh")) return P::Laugh;
    if (Pose == TEXT("sit")) return P::Sit;
    if (Pose == TEXT("walk")) return P::Walk;
    if (Pose == TEXT("sleepy")) return P::Sleepy;
    if (Pose == TEXT("angry")) return P::Angry;
    if (Pose == TEXT("pose")) return P::Pose;
    return P::Idle;
}
double PoseLifetime(const FString& Pose)
{
    if (Pose == TEXT("sit") || Pose == TEXT("sleepy")) return 25.0;
    if (Pose == TEXT("wave")) return 5.5;
    if (Pose == TEXT("walk")) return 6.0;
    if (Pose == TEXT("idle")) return 0.0;
    return 5.0;
}
}

AYunaAvatarActor::AYunaAvatarActor()
{
    PrimaryActorTick.bCanEverTick = true;
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("YunaRoot"));
    SetRootComponent(SceneRoot);

    AvatarMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("YunaSkeletalMesh"));
    AvatarMesh->SetupAttachment(SceneRoot);

    DirectBoneMesh = CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("YunaDirectBonePreview"));
    DirectBoneMesh->SetupAttachment(SceneRoot);
    DirectBoneMesh->SetVisibility(false);
    DirectBoneMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AYunaAvatarActor::BeginPlay()
{
    Super::BeginPlay();
    LastValidStateAt = -1000.0;
    BaseAvatarMeshTransform = AvatarMesh->GetRelativeTransform();
    SyncDirectBonePreview();
}

void AYunaAvatarActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float SafeDelta = FMath::Clamp(DeltaSeconds, 0.f, 0.1f);
    Elapsed += SafeDelta;
    PollAccumulator += SafeDelta;
    if (PollAccumulator >= PollPeriod)
    {
        PollAccumulator = 0.f;
        if (ReadLocalState())
        {
            LastValidStateAt = Elapsed;
        }
    }
    if (Elapsed - LastValidStateAt > StaleAfterSeconds)
    {
        DesiredPose = TEXT("idle");
        DesiredEmotion = TEXT("neutral");
        DesiredEmotionIntensity = 0.f;
        bDesiredSpeaking = false;
        bHasAmplitude = false;
        TargetMouth = 0.f;
    }
    // Gestos curtos não ficam congelados após o clique e o heartbeat.
    if (PoseExpiresAt > 0.0 && Elapsed > PoseExpiresAt)
    {
        DesiredPose = TEXT("idle");
        PoseExpiresAt = 0.0;
    }
    UpdateAnimation(SafeDelta);
}

bool AYunaAvatarActor::ReadLocalState()
{
    // A estrutura do repo é fixa; não há caminho arbitrário vindo do chat.
    const FString File = FPaths::ConvertRelativePathToFull(
        FPaths::Combine(FPaths::ProjectDir(), TEXT("../../data/yuna_unreal_state.json")));
    const int64 Size = IFileManager::Get().FileSize(*File);
    if (Size <= 0 || Size > MaxStateBytes) return false;

    FString Text;
    if (!FFileHelper::LoadFileToString(Text, *File)) return false;
    TSharedPtr<FJsonObject> Data;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
    if (!FJsonSerializer::Deserialize(Reader, Data) || !Data.IsValid()) return false;

    double Version = 0.0, Timestamp = 0.0, Mouth = 0.0, Intensity = 0.0;
    double GestureSequence = 0.0;
    bool Speaking = false, HasAmplitude = false;
    FString Pose, Emotion, Session;
    if (!Data->TryGetStringField(TEXT("session"), Session) ||
        Session.IsEmpty() || Session.Len() > 64 ||
        !Data->TryGetNumberField(TEXT("version"), Version) || Version != 1.0 ||
        !Data->TryGetNumberField(TEXT("updated_at"), Timestamp) ||
        !FMath::IsFinite(Timestamp) ||
        FMath::Abs(static_cast<double>(FDateTime::UtcNow().ToUnixTimestamp()) - Timestamp) > 3.0 ||
        !Data->TryGetNumberField(TEXT("mouth_level"), Mouth) ||
        !FMath::IsFinite(Mouth) ||
        !Data->TryGetNumberField(TEXT("intensity"), Intensity) ||
        !FMath::IsFinite(Intensity) ||
        !Data->TryGetNumberField(TEXT("gesture_seq"), GestureSequence) ||
        !FMath::IsFinite(GestureSequence) || GestureSequence < 0 ||
        GestureSequence > 1000000000 ||
        !Data->TryGetBoolField(TEXT("speaking"), Speaking) ||
        !Data->TryGetBoolField(TEXT("has_amplitude"), HasAmplitude) ||
        !Data->TryGetStringField(TEXT("pose"), Pose) ||
        !Data->TryGetStringField(TEXT("emotion"), Emotion))
    {
        return false;
    }
    if (!IsAllowedPose(Pose)) Pose = TEXT("idle");
    if (!IsAllowedEmotion(Emotion)) Emotion = TEXT("neutral");

    if (LastSession != Session)
    {
        LastSession = Session;
        LastGestureSeq = -1;
        PoseExpiresAt = 0.0;
    }
    const int64 NewSequence = static_cast<int64>(GestureSequence);
    if (LastGestureSeq != NewSequence)
    {
        LastGestureSeq = NewSequence;
        DesiredPose = Pose;
        const double Life = PoseLifetime(Pose);
        PoseExpiresAt = Life > 0.0 ? Elapsed + Life : 0.0;
    }
    DesiredEmotion = Emotion;
    DesiredEmotionIntensity = FMath::Clamp(static_cast<float>(Intensity), 0.f, 1.f);
    bDesiredSpeaking = Speaking;
    bHasAmplitude = HasAmplitude;
    TargetMouth = Speaking ? FMath::Clamp(static_cast<float>(Mouth), 0.f, 1.f) : 0.f;
    return true;
}

FName AYunaAvatarActor::FindBone(const FName& Preferred, const TArray<FName>& Candidates) const
{
    if (!Preferred.IsNone() && DirectBoneMesh->GetBoneIndex(Preferred) >= 0) return Preferred;
    for (const FName& Name : Candidates)
    {
        if (DirectBoneMesh->GetBoneIndex(Name) >= 0) return Name;
    }
    return NAME_None;
}
void AYunaAvatarActor::ResolveBones()
{
    ResolvedHead = FindBone(HeadBone, {TEXT("J_Bip_C_Head"), TEXT("head"), TEXT("Head")});
    ResolvedChest = FindBone(ChestBone,
        {TEXT("J_Bip_C_Chest"), TEXT("chest"), TEXT("Chest"), TEXT("spine2"), TEXT("Spine2")});
    ResolvedLeftArm = FindBone(LeftArmBone,
        {TEXT("J_Bip_L_UpperArm"), TEXT("leftUpperArm"), TEXT("LeftUpperArm"), TEXT("upperarm_l")});
    ResolvedRightArm = FindBone(RightArmBone,
        {TEXT("J_Bip_R_UpperArm"), TEXT("rightUpperArm"), TEXT("RightUpperArm"), TEXT("upperarm_r")});
    ResolvedLeftLeg = FindBone(LeftLegBone,
        {TEXT("J_Bip_L_UpperLeg"), TEXT("leftUpperLeg"), TEXT("LeftUpperLeg"), TEXT("thigh_l")});
    ResolvedRightLeg = FindBone(RightLegBone,
        {TEXT("J_Bip_R_UpperLeg"), TEXT("rightUpperLeg"), TEXT("RightUpperLeg"), TEXT("thigh_r")});
    ResolvedLeftEye = FindBone(LeftEyeBone,
        {TEXT("J_Adj_L_FaceEye"), TEXT("leftEye"), TEXT("Eye_L")});
    ResolvedRightEye = FindBone(RightEyeBone,
        {TEXT("J_Adj_R_FaceEye"), TEXT("rightEye"), TEXT("Eye_R")});
    ResolvedHair = FindBone(HairBone, {TEXT("J_Sec_Hair1"), TEXT("Hair1"), TEXT("hair_01")});
}
bool AYunaAvatarActor::SyncDirectBonePreview()
{
    if (!AvatarMesh || !DirectBoneMesh) return false;
    USkeletalMesh* Asset = AvatarMesh->GetSkeletalMeshAsset();
    if (!bDirectBonePreview || !Asset)
    {
        DirectBoneMesh->SetVisibility(false);
        AvatarMesh->SetVisibility(true);
        return false;
    }
    if (CachedDirectAsset != Asset)
    {
        DirectBoneMesh->SetSkinnedAssetAndUpdate(Asset, true);
        const int32 MaterialCount = AvatarMesh->GetNumMaterials();
        for (int32 Index = 0; Index < MaterialCount; ++Index)
        {
            DirectBoneMesh->SetMaterial(Index, AvatarMesh->GetMaterial(Index));
        }
        CachedDirectAsset = Asset;
        ResolveBones();
    }
    DirectBoneMesh->SetRelativeTransform(BaseAvatarMeshTransform);
    AvatarMesh->SetVisibility(false);
    DirectBoneMesh->SetVisibility(true);
    return true;
}
void AYunaAvatarActor::RotateBone(const FName& Bone, const FRotator& Delta) const
{
    if (Bone.IsNone() || DirectBoneMesh->GetBoneIndex(Bone) < 0) return;
    const FRotator Base = DirectBoneMesh->GetBoneRotationByName(
        Bone, EBoneSpaces::ComponentSpace);
    const FQuat Rotation = Delta.Quaternion() * Base.Quaternion();
    DirectBoneMesh->SetBoneRotationByName(
        Bone, Rotation.Rotator(), EBoneSpaces::ComponentSpace);
}

void AYunaAvatarActor::UpdateAnimation(float DeltaSeconds)
{
    const YunaMotion::FFrame Frame = YunaMotion::Sample({
        static_cast<float>(Elapsed),
        DecodePose(DesiredPose),
        TargetMouth,
        DesiredEmotionIntensity,
        bDesiredSpeaking,
        bHasAmplitude,
        bReducedMotion
    });
    Signals.Pose = DesiredPose;
    Signals.Emotion = DesiredEmotion;
    Signals.EmotionIntensity = DesiredEmotionIntensity;
    Signals.bSpeaking = bDesiredSpeaking;
    Signals.Mouth = FMath::FInterpTo(Signals.Mouth, Frame.Mouth, DeltaSeconds, 14.f);
    Signals.Breath = Frame.Breath;
    Signals.BodySway = Frame.BodySway;
    Signals.BodyBob = Frame.BodyBob;
    Signals.HeadYaw = Frame.HeadYaw;
    Signals.HeadPitch = Frame.HeadPitch;
    Signals.HeadTilt = Frame.HeadTilt;
    Signals.EyeYaw = Frame.EyeYaw;
    Signals.EyePitch = Frame.EyePitch;
    Signals.Blink = FMath::Max(Frame.BlinkLeft, Frame.BlinkRight);
    Signals.BlinkLeft = Frame.BlinkLeft;
    Signals.BlinkRight = Frame.BlinkRight;
    Signals.Wave = Frame.Wave;
    Signals.LeftArm = Frame.LeftArm;
    Signals.RightArm = Frame.RightArm;
    Signals.LeftLeg = Frame.LeftLeg;
    Signals.RightLeg = Frame.RightLeg;
    Signals.HairSway = Frame.HairSway;

    // Atualizar os ossos na própria malha quando um AnimBlueprint ainda não existe.
    if (SyncDirectBonePreview())
    {
        DirectBoneMesh->CopyPoseFromSkeletalComponent(AvatarMesh);
        DirectBoneMesh->SetRelativeLocation(
            BaseAvatarMeshTransform.GetLocation() +
            FVector(0.f, Signals.BodySway * 9.f,
                    (Signals.Breath + Signals.BodyBob) * 30.f));
        DirectBoneMesh->SetRelativeRotation(
            BaseAvatarMeshTransform.Rotator() +
            FRotator(0.f, Signals.BodySway * 30.f, 0.f));
        RotateBone(ResolvedHead,
            FRotator(Signals.HeadPitch, Signals.HeadYaw, Signals.HeadTilt));
        RotateBone(ResolvedChest,
            FRotator(Signals.Breath * 70.f, 0.f, Signals.BodySway * 35.f));
        RotateBone(ResolvedLeftArm, FRotator(Signals.LeftArm, 0.f, 0.f));
        RotateBone(ResolvedRightArm, FRotator(Signals.RightArm, 0.f, 0.f));
        RotateBone(ResolvedLeftLeg, FRotator(Signals.LeftLeg, 0.f, 0.f));
        RotateBone(ResolvedRightLeg, FRotator(Signals.RightLeg, 0.f, 0.f));
        RotateBone(ResolvedLeftEye,
            FRotator(Signals.EyePitch, Signals.EyeYaw, 0.f));
        RotateBone(ResolvedRightEye,
            FRotator(Signals.EyePitch, Signals.EyeYaw, 0.f));
        RotateBone(ResolvedHair, FRotator(0.f, 0.f, Signals.HairSway));
    }
    else if (AvatarMesh)
    {
        // O modo Animation Blueprint preserva morph targets, física e retargeting.
        AvatarMesh->SetRelativeLocation(
            BaseAvatarMeshTransform.GetLocation() +
            FVector(0.f, 0.f, (Signals.Breath + Signals.BodyBob) * 30.f));
        AvatarMesh->SetRelativeRotation(
            BaseAvatarMeshTransform.Rotator() +
            FRotator(0.f, Signals.BodySway * 30.f, 0.f));
        AvatarMesh->SetMorphTarget(MouthMorphName, Signals.Mouth);
        if (LeftBlinkMorphName.IsNone() || RightBlinkMorphName.IsNone())
        {
            AvatarMesh->SetMorphTarget(BlinkMorphName, Signals.Blink);
        }
        else
        {
            AvatarMesh->SetMorphTarget(LeftBlinkMorphName, Signals.BlinkLeft);
            AvatarMesh->SetMorphTarget(RightBlinkMorphName, Signals.BlinkRight);
        }
        AvatarMesh->SetMorphTarget(
            HappyMorphName,
            Signals.Emotion == TEXT("happy") ? Signals.EmotionIntensity : 0.f);
        if (UYunaAnimInstance* Anim = Cast<UYunaAnimInstance>(AvatarMesh->GetAnimInstance()))
        {
            Anim->Signals = Signals;
        }
    }
    OnYunaSignalsChanged(Signals);
}
