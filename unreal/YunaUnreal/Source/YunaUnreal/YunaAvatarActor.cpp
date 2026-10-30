#include "YunaAvatarActor.h"

#include "YunaAnimInstance.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
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

float BlinkPulse(float Time, float Center)
{
    return FMath::Clamp(1.f - FMath::Abs(Time - Center) / 0.13f, 0.f, 1.f);
}
}

AYunaAvatarActor::AYunaAvatarActor()
{
    PrimaryActorTick.bCanEverTick = true;
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("YunaRoot"));
    SetRootComponent(SceneRoot);
    AvatarMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("YunaSkeletalMesh"));
    AvatarMesh->SetupAttachment(SceneRoot);
}

void AYunaAvatarActor::BeginPlay()
{
    Super::BeginPlay();
    // Mesmo sem Python aberto, a animação ambiente permanece funcionando.
    LastValidStateAt = -1000.0;
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
        TargetMouth = 0.f;
    }
    UpdateAnimation(SafeDelta);
}

bool AYunaAvatarActor::ReadLocalState()
{
    // Localização fixa: o projeto Unreal fica em Projeto-Yuna/unreal/YunaUnreal/.
    const FString File = FPaths::ConvertRelativePathToFull(
        FPaths::Combine(FPaths::ProjectDir(), TEXT("../../data/yuna_unreal_state.json")));
    const int64 Size = IFileManager::Get().FileSize(*File);
    if (Size <= 0 || Size > MaxStateBytes)
    {
        return false;
    }
    FString Text;
    if (!FFileHelper::LoadFileToString(Text, *File))
    {
        return false;
    }
    TSharedPtr<FJsonObject> Data;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
    if (!FJsonSerializer::Deserialize(Reader, Data) || !Data.IsValid())
    {
        return false;
    }

    double Version = 0.0;
    double Timestamp = 0.0;
    double Mouth = 0.0;
    double Intensity = 0.0;
    bool Speaking = false;
    FString Pose;
    FString Emotion;
    if (!Data->TryGetNumberField(TEXT("version"), Version) || Version != 1.0 ||
        !Data->TryGetNumberField(TEXT("updated_at"), Timestamp) ||
        !FMath::IsFinite(Timestamp) ||
        FMath::Abs(FDateTime::UtcNow().ToUnixTimestamp() - Timestamp) > 3.0 ||
        !Data->TryGetNumberField(TEXT("mouth_level"), Mouth) ||
        !FMath::IsFinite(Mouth) ||
        !Data->TryGetNumberField(TEXT("intensity"), Intensity) ||
        !FMath::IsFinite(Intensity) ||
        !Data->TryGetBoolField(TEXT("speaking"), Speaking) ||
        !Data->TryGetStringField(TEXT("pose"), Pose) ||
        !Data->TryGetStringField(TEXT("emotion"), Emotion))
    {
        return false;
    }
    DesiredPose = IsAllowedPose(Pose) ? Pose : TEXT("idle");
    DesiredEmotion = IsAllowedEmotion(Emotion) ? Emotion : TEXT("neutral");
    DesiredEmotionIntensity = FMath::Clamp(static_cast<float>(Intensity), 0.f, 1.f);
    bDesiredSpeaking = Speaking;
    TargetMouth = Speaking ? FMath::Clamp(static_cast<float>(Mouth), 0.f, 1.f) : 0.f;
    return true;
}

void AYunaAvatarActor::UpdateAnimation(float DeltaSeconds)
{
    const float T = static_cast<float>(Elapsed);
    Signals.Pose = DesiredPose;
    Signals.Emotion = DesiredEmotion;
    Signals.EmotionIntensity = DesiredEmotionIntensity;
    Signals.bSpeaking = bDesiredSpeaking;
    Signals.Mouth = FMath::FInterpTo(Signals.Mouth, TargetMouth, DeltaSeconds, 14.f);
    Signals.Breath = FMath::Sin(T * (Signals.Pose == TEXT("sleepy") ? 0.85f : 1.65f)) * 0.025f;
    Signals.BodySway = FMath::Sin(T * 0.61f) * 0.018f + FMath::Sin(T * 0.93f) * 0.008f;
    Signals.HeadYaw = FMath::Sin(T * 0.49f) * 5.f + FMath::Sin(T * 0.17f) * 3.f;
    Signals.HeadPitch = FMath::Sin(T * 0.72f) * 2.f +
        (Signals.Pose == TEXT("curious") ? -7.f : 0.f);
    const float BlinkPhase = FMath::Fmod(T, 20.f);
    Signals.Blink = FMath::Max(
        FMath::Max(BlinkPulse(BlinkPhase, 4.4f), BlinkPulse(BlinkPhase, 9.2f)),
        FMath::Max(BlinkPulse(BlinkPhase, 9.5f), BlinkPulse(BlinkPhase, 15.1f)));
    if (Signals.Pose == TEXT("sleepy"))
    {
        Signals.Blink = 1.f;
    }
    Signals.Wave = Signals.Pose == TEXT("wave")
        ? 0.65f + FMath::Sin(T * 7.f) * 0.3f : 0.f;

    // O corpo inteiro se move um pouco; o rig facial/ossos pode utilizar Signals
    // num Animation Blueprint derivado de UYunaAnimInstance.
    AvatarMesh->SetRelativeLocation(FVector(0.f, 0.f, Signals.Breath * 30.f));
    AvatarMesh->SetRelativeRotation(FRotator(0.f, Signals.BodySway * 22.f, 0.f));
    AvatarMesh->SetMorphTarget(BlinkMorphName, Signals.Blink);
    AvatarMesh->SetMorphTarget(MouthMorphName, Signals.Mouth);
    AvatarMesh->SetMorphTarget(HappyMorphName,
        Signals.Emotion == TEXT("happy") ? Signals.EmotionIntensity : 0.f);

    if (UYunaAnimInstance* Anim = Cast<UYunaAnimInstance>(AvatarMesh->GetAnimInstance()))
    {
        Anim->Signals = Signals;
    }
    OnYunaSignalsChanged(Signals);
}
