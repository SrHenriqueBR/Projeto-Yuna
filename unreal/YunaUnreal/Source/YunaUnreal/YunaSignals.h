#pragma once

#include "CoreMinimal.h"
#include "YunaSignals.generated.h"

// Dados visuais e não privilegiados. Nenhum campo de conversa, webcam ou memória.
USTRUCT(BlueprintType)
struct FYunaSignals
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    FString Pose = TEXT("idle");

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    FString Emotion = TEXT("neutral");

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float EmotionIntensity = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    bool bSpeaking = false;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float Mouth = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float Blink = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float Breath = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float HeadYaw = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float HeadPitch = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float BodySway = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float Wave = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float BlinkLeft = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float BlinkRight = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float HeadTilt = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float EyeYaw = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float EyePitch = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float BodyBob = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float LeftArm = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float RightArm = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float LeftLeg = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float RightLeg = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="Yuna|Animation")
    float HairSway = 0.f;
};
