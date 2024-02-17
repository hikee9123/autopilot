using Cxx = import "./include/c++.capnp";
$Cxx.namespace("cereal");

using Car = import "car.capnp";

@0xb526ba661d550a59;

# custom.capnp: a home for empty structs reserved for custom forks
# These structs are guaranteed to remain reserved and empty in mainline
# cereal, so use these if you want custom events in your fork.

# you can rename the struct, but don't change the identifier
struct CarStateCustom @0x81c2f05a394cf4af {

  tpms @0 :Tpms;
  alertTextMsg1  @1 :Text;
  alertTextMsg2  @2 :Text;
  alertTextMsg3  @3 :Text;

  electGearStep @4 :Int16;
  supportedCars @5 :List(Text);

  breakPos @6 :Float32;

  struct Tpms {
    unit @0 :Int16;
    fl @1 :Float32;
    fr @2 :Float32;
    rl @3 :Float32;
    rr @4 :Float32;
}

}

struct CarControlCustom @0xaedffd8f31e7b55d {
    
}

struct NaviCustom @0xf35cc4560bbf6ec2 {
    # neokii
    naviData @0 :NaviData;


    struct NaviData {
        active @0 :Int16;
        roadLimitSpeed @1 :Int16;
        isHighway @2 :Bool;
        camType @3 :Int16;
        camLimitSpeedLeftDist @4 :Int16;
        camLimitSpeed @5 :Int16;
        sectionLimitSpeed @6 :Int16;
        sectionLeftDist @7 :Int16;
        sectionAvgSpeed @8 :Int16;
        sectionLeftTime @9 :Int16;
        sectionAdjustSpeed @10 :Bool;
        camSpeedFactor @11 :Float32;
        currentRoadName @12 :Text;
        isNda2 @13 :Bool;
        cntIdx @14 :Int16;
    }       
}

struct UICustom @0xda96579883444c35 {
    community @0 :Community;
    userInterface @1 :UserInterface;
    debug @2 :Debug;


    struct Community
    {
       cmdIdx @0 :Int16;
       cruiseMode @1 :Int16;
       cruiseGap @2 :Int16;
    }

    struct UserInterface
    {
       cmdIdx @0 :Int16;      
       showDebugMessage @1 :Int16;
       showCarTracking @2 :Int16;
       tpms @3 :Int16;
       debug @4 :Int16;
       kegman @5 :Int16;
       kegmanCPU @6 :Int16;
       kegmanBattery @7 :Int16;
       kegmanGPU @8 :Int16;
       kegmanAngle @9 :Int16;
       kegmanEngine @10 :Int16;
       kegmanDistance @11 :Int16;
       kegmanSpeed @12 :Int16;    
    }

    struct Debug
    {
       cmdIdx @0 :Int16;         
       idx1 @1 :Int16;
       idx2 @2 :Int16;
       idx3 @3 :Int16;
       idx4 @4 :Int16;
       idx5 @5 :Int16;
       idx6 @6 :Int16;
    }          
}

struct CustomReserved4 @0x80ae746ee2596b11 {
}

struct CustomReserved5 @0xa5cd762cd951a455 {
}

struct CustomReserved6 @0xf98d843bfd7004a3 {
}

struct CustomReserved7 @0xb86e6369214c01c8 {
}

struct CustomReserved8 @0xf416ec09499d9d19 {
}

struct CustomReserved9 @0xa1680744031fdb2d {
}
