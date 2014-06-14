#include "ofApp.h"

void ofApp::setup()
{
    ofSetWindowPosition(ofGetScreenWidth()-ofGetWidth()-100, ofGetScreenHeight()-ofGetHeight()-300);
	

	transparent.afterMainSetup(ofxTransparentWindow::SCREENSAVER);
	ofSetFullscreen(true);
    
    // listen on the given port
	cout << "listening for osc messages on port " << PORT << "\n";
	receiver.setup(PORT); // listen to the PORT
    
    
    oscMessagetoDisplay.init("fonts/Pigiarniq Heavy.ttf",60); // seting up font type and size

    lastTime = 0;
    enableMsgSys = false;
    
}

void ofApp::update()
{
    transparent.update();
    
    
    // check for waiting messages
	while(receiver.hasWaitingMessages()){
		// get the next message
        
		ofxOscMessage m;
		receiver.getNextMessage(&m);
        
		// string message check
		if(m.getAddress() == "/airmsg/response"){
            
			// one string Message in the package
            string msg = m.getArgAsString(0); // here the message comes
            msg_strings.push_back(msg);
           // cout << msg << endl;
            lastTime = ofGetElapsedTimeMillis();
        }
    }
    
}

void ofApp::draw()
{
    if(!enableMsgSys){ //check if it is enable or disable
        
        if(msg_strings.size() > 0){
            
            if(ofGetElapsedTimeMillis() - lastTime < MSG_TIME){
                oscMessagetoDisplay.setText(msg_strings[0]);
                oscMessagetoDisplay.setColor(0,0,0,0);
                oscMessagetoDisplay.wrapTextX(ofGetWidth());
                
                ofPushMatrix();
                    ofTranslate(0, 0, 0);
                
                    //background transparent white rectangle
                    ofSetColor(255,255,255,150);
                    ofFill();
                    ofRect(ofGetWidth()/2 - oscMessagetoDisplay.getWidth()/2 , ofGetHeight()/2-oscMessagetoDisplay.getHeight()/2, oscMessagetoDisplay.getWidth(), oscMessagetoDisplay.getHeight());

                    //draw de text
                    oscMessagetoDisplay.drawCenter(ofGetWidth()/2,ofGetHeight()/2-oscMessagetoDisplay.getHeight()/2);
                ofPopMatrix();
                
            } else {
                msg_strings.erase(msg_strings.begin()); //delete first message after exhibit it
                lastTime = ofGetElapsedTimeMillis(); //reset timer
            }
            
        }

    }
}

void ofApp::keyPressed(int key){

    switch (key) {
        case 'e':
            enableMsgSys = !enableMsgSys;
            lastTime = ofGetElapsedTimeMillis(); //reset timer
            break;
            
    }


}
void ofApp::keyReleased(int key){}
void ofApp::mouseMoved(int x, int y){}
void ofApp::mouseDragged(int x, int y, int button){}
void ofApp::mousePressed(int x, int y, int button){}
void ofApp::mouseReleased(int x, int y, int button){}
void ofApp::windowResized(int w, int h){}
void ofApp::gotMessage(ofMessage msg){}
void ofApp::dragEvent(ofDragInfo dragInfo){}