#pragma once

#include "ofMain.h"
#include "ofxOsc.h"

#include "ofxTransparentWindow.h"
#include "ofxTextSuite.h"

// listen on port 8888
#define PORT 8888

#define MSG_TIME 2000 //max time per message in milliseconds

class ofApp : public ofBaseApp
{
public:
    
    void setup();
    void update();
    void draw();
    
    void keyPressed(int key);
    void keyReleased(int key);
    void mouseMoved(int x, int y);
    void mouseDragged(int x, int y, int button);
    void mousePressed(int x, int y, int button);
    void mouseReleased(int x, int y, int button);
    void windowResized(int w, int h);
    void dragEvent(ofDragInfo dragInfo);
    void gotMessage(ofMessage msg);
    
    
private:
    
    ofxTransparentWindow transparent;
    
    ofxOscReceiver receiver;

    
    ofxTextBlock        oscMessagetoDisplay;
    vector<string> msg_strings;
    long lastTime;
    bool enableMsgSys;
};
