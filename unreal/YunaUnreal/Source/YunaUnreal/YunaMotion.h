#pragma once
// Matematica pura C++17: sem Unreal nem rede. Os testes rodam fora da engine.
#include <algorithm>
#include <cmath>

namespace YunaMotion
{
enum class EPose {
    Idle, Happy, Curious, Surprised, Shy, Wave, Talk, Wink,
    Laugh, Sit, Walk, Sleepy, Angry, Pose
};

struct FInput {
    float Seconds = 0.f;
    EPose Pose = EPose::Idle;
    float MouthLevel = 0.f;
    float EmotionIntensity = 0.f;
    bool bSpeaking = false;
    bool bHasAmplitude = false;
    bool bReduceMotion = false;
};

struct FFrame {
    float Breath = 0.f;
    float BodySway = 0.f;
    float BodyBob = 0.f;
    float HeadYaw = 0.f;
    float HeadPitch = 0.f;
    float HeadTilt = 0.f;
    float EyeYaw = 0.f;
    float EyePitch = 0.f;
    float BlinkLeft = 0.f;
    float BlinkRight = 0.f;
    float Mouth = 0.f;
    float Wave = 0.f;
    float LeftArm = 0.f;
    float RightArm = 0.f;
    float LeftLeg = 0.f;
    float RightLeg = 0.f;
    float HairSway = 0.f;
};

inline float Clamp(float V, float Lo, float Hi) {
    return std::max(Lo, std::min(V, Hi));
}
inline float SmoothStep(float V) {
    const float T = Clamp(V, 0.f, 1.f);
    return T * T * (3.f - 2.f * T);
}
inline float Pulse(float T, float Center, float Width = 0.14f) {
    return Clamp(1.f - std::fabs(T - Center) / Width, 0.f, 1.f);
}
inline float LookTarget(float Seconds) {
    struct FStop { float At, Value; };
    constexpr FStop Stops[] = {
        {0.f, 0.f}, {2.1f, 0.f}, {3.f, -7.f}, {5.2f, -7.f},
        {6.2f, 4.f}, {9.f, 4.f}, {10.f, 0.f}, {12.7f, 0.f},
        {13.7f, 8.f}, {16.2f, 8.f}, {18.4f, 0.f}, {20.f, 0.f}
    };
    const float Phase = std::fmod(std::max(0.f, Seconds), 20.f);
    for (unsigned I = 1; I < sizeof(Stops) / sizeof(Stops[0]); ++I) {
        if (Phase <= Stops[I].At) {
            const float Range = Stops[I].At - Stops[I - 1].At;
            const float Alpha = SmoothStep((Phase - Stops[I - 1].At) / Range);
            return Stops[I - 1].Value +
                   (Stops[I].Value - Stops[I - 1].Value) * Alpha;
        }
    }
    return 0.f;
}

inline FFrame Sample(FInput In) {
    FFrame Out;
    if (!std::isfinite(In.Seconds)) In.Seconds = 0.f;
    if (!std::isfinite(In.MouthLevel)) In.MouthLevel = 0.f;
    if (!std::isfinite(In.EmotionIntensity)) In.EmotionIntensity = 0.f;
    const float T = std::max(0.f, In.Seconds);
    const bool Sleepy = In.Pose == EPose::Sleepy;
    const bool Seated = In.Pose == EPose::Sit || Sleepy;
    const float Pace = Sleepy ? 0.6f : (Seated ? 0.84f : 1.f);
    const float Slow = std::sin(T * 0.53f) * 0.74f +
                       std::sin(T * 0.31f + 0.9f) * 0.26f;

    if (!In.bReduceMotion) {
        Out.Breath = std::sin(T * 1.62f * Pace) * (Sleepy ? 0.018f : 0.025f);
        Out.BodySway = Slow * (Seated ? 0.012f : 0.031f);
        Out.BodyBob = Seated ? 0.f : std::sin(T * 1.27f) * 0.009f;
        Out.HeadYaw = LookTarget(T) + Slow * 1.3f;
        Out.HeadPitch = std::sin(T * 0.68f) * 1.45f +
            (In.Pose == EPose::Curious ? -6.5f : 0.f);
        Out.HeadTilt = Slow * 1.6f + (In.Pose == EPose::Shy ? -5.f : 0.f);
        Out.EyeYaw = LookTarget(T) * 1.15f;
        Out.EyePitch = std::sin(T * 0.7f + 1.f) * 1.3f;
        Out.LeftArm = std::sin(T * 0.92f + 0.3f) * 2.8f;
        Out.RightArm = std::sin(T * 0.88f + 1.6f) * 2.5f;
        Out.LeftLeg = Seated ? 27.f : std::sin(T * 0.51f) * 1.1f;
        Out.RightLeg = Seated ? 27.f : -std::sin(T * 0.51f) * 1.1f;
        Out.HairSway = std::sin(T * 0.83f + 0.6f) * 1.5f;
        const float B = std::fmod(T, 21.6f);
        const float Blink = std::max(
            std::max(Pulse(B, 3.12f), Pulse(B, 7.03f)),
            std::max(std::max(Pulse(B, 10.45f), Pulse(B, 10.75f)),
                     std::max(Pulse(B, 15.28f), Pulse(B, 19.1f))));
        Out.BlinkLeft = Blink;
        Out.BlinkRight = Blink;
        if (In.Pose == EPose::Wave) {
            Out.Wave = 0.5f + 0.5f * std::sin(T * 7.5f);
            Out.RightArm = -48.f - Out.Wave * 11.f;
            Out.HeadTilt += 4.f;
        } else if (In.Pose == EPose::Walk) {
            Out.LeftLeg = std::sin(T * 5.7f) * 18.f;
            Out.RightLeg = -Out.LeftLeg;
            Out.LeftArm = -Out.LeftLeg * 0.42f;
            Out.RightArm = Out.LeftLeg * 0.42f;
            Out.BodyBob = std::fabs(std::sin(T * 5.7f)) * 0.035f;
        } else if (In.Pose == EPose::Shy) {
            Out.LeftArm = -17.f; Out.RightArm = -17.f;
        } else if (In.Pose == EPose::Angry) {
            Out.LeftArm = 13.f; Out.RightArm = 13.f;
            Out.HeadPitch += 3.f;
        }
        if (In.Pose == EPose::Wink) {
            Out.BlinkRight = 1.f;
        }
        if (Sleepy) {
            Out.BlinkLeft = 1.f;
            Out.BlinkRight = 1.f;
        }
        if (In.Pose == EPose::Surprised) {
            Out.BlinkLeft *= 0.35f;
            Out.BlinkRight *= 0.35f;
        }
    }
    // Boca só pode mexer enquanto há reprodução real de áudio.
    if (In.bSpeaking) {
        Out.Mouth = In.bHasAmplitude
            ? Clamp(In.MouthLevel, 0.f, 1.f)
            : (In.bReduceMotion ? 0.18f :
                0.13f + 0.24f * (0.5f + 0.5f * std::sin(T * 18.f)));
    }
    return Out;
}
} // namespace YunaMotion
