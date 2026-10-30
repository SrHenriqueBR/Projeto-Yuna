#include "../YunaUnreal/Source/YunaUnreal/YunaMotion.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace YunaMotion;

int main() {
    // O avatar não deve congelar quando o Python estiver ocioso.
    FFrame idleA = Sample({2.0f, EPose::Idle});
    FFrame idleB = Sample({3.0f, EPose::Idle});
    assert(std::fabs(idleA.Breath - idleB.Breath) > 0.004f);
    assert(std::fabs(idleA.HeadYaw - idleB.HeadYaw) > 0.2f);
    assert(std::isfinite(idleB.BodySway));
    assert(std::fabs(idleB.BodySway) < 0.05f);
    assert(std::fabs(idleB.HeadYaw) < 13.f);
    assert(std::fabs(idleB.LeftArm) < 4.f);

    // Piscadas variadas, inclusive duas próximas, sem travar as pálpebras.
    assert(Sample({3.12f, EPose::Idle}).BlinkLeft > 0.99f);
    assert(Sample({7.03f, EPose::Idle}).BlinkRight > 0.99f);
    assert(Sample({10.45f, EPose::Idle}).BlinkLeft > 0.99f);
    assert(Sample({10.75f, EPose::Idle}).BlinkRight > 0.99f);
    assert(Sample({4.0f, EPose::Idle}).BlinkLeft == 0.f);

    // Reações distintas: aceno, caminhada, curiosidade, soneca, piscadinha.
    FFrame wave = Sample({2.0f, EPose::Wave});
    assert(wave.RightArm < -47.f);
    assert(wave.Wave >= 0.f && wave.Wave <= 1.f);
    FFrame walking = Sample({2.0f, EPose::Walk});
    assert(std::fabs(walking.LeftLeg + walking.RightLeg) < 0.0001f);
    assert(std::fabs(walking.LeftLeg) > 5.f);
    FFrame curious = Sample({2.0f, EPose::Curious});
    assert(curious.HeadPitch < -3.f);
    FFrame sleepy = Sample({2.0f, EPose::Sleepy});
    assert(sleepy.BlinkLeft == 1.f && sleepy.BlinkRight == 1.f);
    assert(sleepy.LeftLeg > 20.f);
    FFrame wink = Sample({4.0f, EPose::Wink});
    assert(wink.BlinkRight == 1.f && wink.BlinkLeft == 0.f);

    // A boca mexe somente quando a voz toca; sem envelope há fallback leve.
    assert(Sample({2.0f, EPose::Idle, 0.8f, 0.f, false}).Mouth == 0.f);
    assert(std::fabs(Sample({2.0f, EPose::Idle, 0.8f, 0.f, true, true}).Mouth - 0.8f) < 0.001f);
    FFrame synth = Sample({2.0f, EPose::Idle, 0.f, 0.f, true, false});
    assert(synth.Mouth >= 0.13f && synth.Mouth <= 0.37f);
    assert(Sample({2.0f, EPose::Idle, 7.f, 0.f, true, true}).Mouth == 1.f);

    // Preferência de movimento reduzido respeitada até com voz habilitada.
    FFrame reduced = Sample({2.0f, EPose::Wave, 0.f, 0.f, true, false, true});
    assert(reduced.BodySway == 0.f);
    assert(reduced.Breath == 0.f);
    assert(reduced.BlinkLeft == 0.f);
    assert(reduced.Wave == 0.f);
    assert(reduced.Mouth == 0.18f);

    FFrame sanitized = Sample({NAN, EPose::Idle, INFINITY, NAN, true, true});
    assert(std::isfinite(sanitized.Mouth));
    assert(std::isfinite(sanitized.Breath));

    std::cout << "YunaMotion: 29 checks OK\n";
}
