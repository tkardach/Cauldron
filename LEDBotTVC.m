//
//  LEDBotTVC.m
//  Fin6LEDBot
//
//  Created by jim kardach on 8/26/16.
//  Copyright © 2016 Forkbeardlabs. All rights reserved.
//
/*
 Enter here with a connected BLE peripherial
 
 ** New **
 Bluetooth protocol - all commands are three bytes:
 command, Data0, Data1:
 0x00: firmware version
 0x01: Start/Stop
 ```0- stop
 1- play
 0x02: Mode
 1- Darts on
 2- Darts blink
 3- dart banks run
 4- dart single led run
 5- dart duel led run
 6- dart broadway flash
 0x03: Dart 1: r, g
 0x04: Dart 1: b
 0x05: Dart 2: r, g
 0x06: Dart 2: b
 0x07: Dart 3: r, g
 0x08: Dart 3: b
 0x09: Dart 4: r, g
 0x0a: Dart 4: b
 0x0b: Dart 5: r, g
 0x0c: Dart 5: b
 0x0d: bg: r, g
 0x0e: bg: b

 0x0f: brightness (all)
 */


#import "LEDBotTVC.h"
#import "BLE.h"
#import "LED.h"
#import "ConfigVC.h"
#import "AppDelegate.h"


@interface LEDBotTVC () <BLEDelegate, UIPickerViewDelegate, UIPickerViewDataSource>
@property (weak, nonatomic) IBOutlet UIButton *playButton;
@property (weak, nonatomic) IBOutlet UIButton *stopButton;
@property (weak, nonatomic) IBOutlet UIButton *resetButton;
@property (weak, nonatomic) IBOutlet UIBarButtonItem *configButton;

@property (weak, nonatomic) IBOutlet UILabel *statusLabel;
@property (weak, nonatomic) IBOutlet UILabel *rssiLabel;
@property (weak, nonatomic) IBOutlet UILabel *versionLabel;
@property (weak, nonatomic) IBOutlet UILabel *bleNameLabel;
@property (weak, nonatomic) IBOutlet UILabel *firmwareLabel;

@property (weak, nonatomic) IBOutlet UIPickerView *ledConfigPicker;
@property (weak, nonatomic) IBOutlet UISlider *brightnessSlider;

@property (strong, nonatomic) NSTimer *rssTimer;
@property (nonatomic) BOOL configEnabled;
@property (nonatomic, strong) NSArray *modes;
//@property (nonatomic, strong) NSArray *modeKeys;
@property (nonatomic) int selectedMode;
@property (nonatomic) int brightness;
@property (nonatomic, strong) LED* activeConfig;

@end

@implementation LEDBotTVC

#pragma mark - setters/getters
- (NSArray *)modes
{
    _modes = @[@"All Off",
               @"All On",
               @"All Blink",
               @"Running 2 Lights",
               @"Fire",
               @"Broadway",
               @"Show1",
               @"All On Dart Color",
               @"Palette Show",
               @"Rainbow Show"];
    return _modes;
}

#pragma mark - view lifecycle
- (void)viewDidLoad {
    [super viewDidLoad];
    self.configEnabled = YES;
    self.ledConfigPicker.delegate = self;

}

- (void)viewWillAppear:(BOOL)animated
{
    [super viewWillAppear:animated];
    
    self.ble.delegate = self;           // setup delegate for BLE class
    self.bleNameLabel.text = self.ble.activePeripheral.name;
    
    self.brightnessSlider.value = self.brightness;
    self.brightnessSlider.maximumValue = 255;
    self.brightnessSlider.minimumValue = 0;
    
    
    // setup the configuration button
    self.configButton.title = @"\u2699";
    UIFont *f1 = [UIFont fontWithName:@"Helvetica" size:24.0];
    NSDictionary *dict = [[NSDictionary alloc] initWithObjectsAndKeys:
                          f1, NSFontAttributeName, nil];
    [self.configButton setTitleTextAttributes:dict forState:UIControlStateNormal];
    
    // configure pause, stop and play buttons (stop state)
    [self modifyButtonState:@"Stop"];
    
    
    
    // Schedule to read RSSI every 1 sec.
    self.rssTimer = [NSTimer scheduledTimerWithTimeInterval:(float)1.0
                                                     target:self selector:@selector(readRSSITimer:)
                                                   userInfo:nil
                                                    repeats:YES];
}

- (void)viewDidAppear:(BOOL)animated
{
    [super viewDidAppear:animated];
    self.selectedMode = 0;  // default is on
    // initialize the colors in the LEDBot
    for (LED* actCfg in self.ledConfigs.configs) {
        self.activeConfig = actCfg;
        [self writeBLE_RG];
        [self writeBLE_B];
        self.selectedMode++;
    }
    self.selectedMode = [self getIndexFromLastConfig];
}

- (void)didReceiveMemoryWarning {
    [super didReceiveMemoryWarning];
    // Dispose of any resources that can be recreated.
}

#pragma mark - Table view data source

- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView
{
    return 1;
}

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
    return 5;
}

- (void) viewWillDisappear:(BOOL)animated
{
    [super viewWillDisappear:animated];
    
    // stop the timer
    [self.rssTimer invalidate];
    self.rssTimer = nil;
    
}

- (void) viewDidDisappear:(BOOL)animated
{
    [super viewDidDisappear:animated];
    AppDelegate *appDelegate = (AppDelegate *)[UIApplication sharedApplication].delegate;
    [appDelegate saveModel];        // save BLE
    
}


-(void)willMoveToParentViewController:(UIViewController *)parent {
    [super willMoveToParentViewController:parent];
    if (!parent){
        // The back button was pressed or interactive gesture used
        [self.ble disconnectPeripheral:self.ble.activePeripheral];  // disconnect the device
    }
}

#pragma mark - BLE delegate
- (void)bleDidDisconnect
{
    //printf("BLE Device Disconnected, LEDBotTVC\n");
    [self popControllersNumber:1];      // go back to ScanTVC
}

// When RSSI is changed, this will be called
-(void) bleDidUpdateRSSI:(NSNumber *) rssi
{
    self.rssiLabel.text = [NSString stringWithFormat:@"RSSI: %@", rssi];
}

-(void) readRSSITimer:(NSTimer *)timer
{
    [self.ble readRSSI];
}

// When connected, this will be called
-(void) bleDidConnect
{
    //printf("BLE Device Connected\n");
    
    // send reset
    UInt8 buf[] = {0x05, 0x00, 0x00};
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
}

#pragma mark - BLE Connection methods

-(void) bleFinishedScan:(BOOL)status
{
    // finsihed finding BLE devices, stop refresh
    // in case transfer before the scan finishes
    
}

// When data is coming, this will be called
-(void) bleDidReceiveData:(unsigned char *)data length:(int)length
{
    //printf("Receive Data: Length: %d\n", length);
    
    // parse data, all commands are in 3-byte
    for (int i = 0; i < length; i+=3)
    {
        printf("%s: 0x%02X, 0x%02X, 0x%02X\n", [[self byteToCommand:data[i]] UTF8String], data[i], data[i+1], data[i+2]);
        
        if (data[i] == 0x00)   // updated firmware version
        {
            UInt16 value;
            value = data[i+2] | data[i+1] << 8;
            self.versionLabel.text = [NSString stringWithFormat:@"FW Ver: %0.1f", (float) (value/10.0)];
            //printf("firmware updated");
        }  else if (data[i] == 0x01)    // command 0x01: data2: stopped(0), playing(1), or reset(2)
        {
            if (data[i+2] == 0x00) {            // stopped
                [self modifyButtonState:@"Stop"];
                printf("Stop button is on\n");
                
            } else if (data[i+2] == 0x01) {     // playing
                [self modifyButtonState:@"Play"];
                printf("Play button is on\n");
            } else if (data[i+2] == 0x02) {     // reset
                [self modifyButtonState:@"Reset"];
                printf("Reset, Stop button is on\n");
            }
        }
        /*
        else if (data[i] == 0x02)   // Mode
        {
            UInt16 value = data[i+2] | data[i+1] << 8;
            self.selectedMode = (int)value;
            // set picker to the new mode
            [self.ledConfigPicker reloadAllComponents];
            [self.ledConfigPicker selectRow:value inComponent:0 animated:YES];
            
        } else if (data[i] == 0x03)   // Dart 1 RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[0] index:i];
        } else if (data[i] == 0x04)   // Dart 1 B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[0] index:i];
        } else if (data[i] == 0x05) // Dart 2 RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[1] index:i];
        } else if (data[i] == 0x06) // Dart 2 B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[1] index:i];
        } else if (data[i] == 0x07) // Dart 3 RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[2] index:i];
        } else if (data[i] == 0x08) // Dart 3 B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[2] index:i];
        } else if (data[i] == 0x09) // Dart 4 RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[3] index:i];
        } else if (data[i] == 0x0a) // Dart 4 B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[3] index:i];
        } else if (data[i] == 0x0b) // Dart 5 RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[4] index:i];
        } else if (data[i] == 0x0c) // Dart 5 B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[4] index:i];
        } else if (data[i] == 0x0d) // background RG
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[5] index:i];
        } else if (data[i] == 0x0e) // background B
        {
            [self setLEDs:data dartConfig:self.ledConfigs.configs[5] index:i];
        } else if (data[i] == 0x0f) // All Brightness
        {
            self.brightness = data[i+2];
            self.brightnessSlider.value = data[i+2];
        }
         */
    }
}

//- (void)setLEDs:(unsigned char *)data dartConfig:(LED *)dart index:(int)i
//{
//    dart.red = data[i+1];
//    dart.green = data[i+2];
//}


-(void)modifyButtonState:(NSString *) button
{
    self.playButton.selected = NO;
    self.stopButton.selected = NO;
    if ([button isEqualToString:@"Play"]) {
        self.playButton.selected = YES;
        self.statusLabel.text = @"Play";
    } else if ([button isEqualToString:@"Stop"]) {
        self.stopButton.selected = YES;
        self.statusLabel.text = @"Stop";
    } else if ([button isEqualToString:@"Reset"]) {    // else reset, all not selected
        self.stopButton.selected = YES;
        self.statusLabel.text = @"Reset/Stop";
    }
}

-(int)buttonState
{
    int cmd = 0;    // stopped
    if (self.playButton.selected) {
        cmd = 1;    // playing
    }
    return cmd;
}

- (NSString *)byteToCommand: (Byte)data
{
    NSString *command = @"";
    switch (data) {
        case 0x00:
            command = @"0x00: Firmware Revision";
            break;
        case 0x01:
            command = @"0x01: Start(0)/Stop(1)/Reset(2)";
            break;
        case 0x02:
            command = @"0x02: Mode, 0-Off, 1-On, 2-blink, 3-bank run, 4-single run, 5-duel run, 6-broadway";
            break;
        case 0x03:
            command = @"0x03: Dart1: r, g";
            break;
        case 0x04:
            command = @"0x04: Dart1: b, 0";
            break;
        case 0x05:
            command = @"0x05: Dart2: r, g";
            break;
        case 0x06:
            command = @"0x06: Dart2: b, 0";
            break;
        case 0x07:
            command = @"0x07: Dart3: r, g";
            break;
        case 0x08:
            command = @"0x08: Dart3: b, 0";
            break;
        case 0x09:
            command = @"0x09: Dart4: r, g";
            break;
        case 0x0a:
            command = @"0x0a: Dart4: b, 0";
            break;
        case 0x0b:
            command = @"0x0b: Dart5: r, g";
            break;
        case 0x0c:
            command = @"0x0c: Dart6: b, 0";
            break;
        case 0x0d:
            command = @"0x0d: bg: r, g";
            break;
        case 0x0e:
            command = @"0x0e: bg: b, 0";
            break;
        case 0x0f:
            command = @"0x1b: brightness All";
            break;
            
        default:
            break;
    }
    return command;
}

- (IBAction)playAction:(UIButton *)sender
{
    if (self.playButton.selected)   // if already selected return
        return;
    [self modifyButtonState:@"Play"];     // set play state
    
    UInt8 buf[3] = {0x01, 0x00, 0x01};  // prepare command
    self.configEnabled = NO;        // disable config mode (during test)
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
}

- (IBAction)stopAction:(UIButton *)sender
{
    if (self.stopButton.selected)   // if already selected return
        return;
    self.configEnabled = YES;       // enable config mode (no test)
    [self modifyButtonState:@"Stop"];
    UInt8 buf[3] = {0x01, 0x00, 0x00};      // prepare command
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
}


- (IBAction)resetButton:(UIButton *)sender
{
    self.configEnabled = YES;       // enable config mode (no test)
    UInt8 buf[3] = {0x01, 0x00, 0x02};
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
    
}

#pragma mark - UIPickerView Delegate Methods
// returns the number of columns to display
- (NSInteger)numberOfComponentsInPickerView:(UIPickerView *)pickerView
{
    return 1;
}

//return number of modes
- (NSInteger)pickerView:(UIPickerView *)pickerView
numberOfRowsInComponent:(NSInteger)component
{
    return [self.modes count];  // number of servos
}

// show keys
-(NSString *)pickerView:(UIPickerView *)pickerView
            titleForRow:(NSInteger)row
           forComponent:(NSInteger)component
{
    NSString *key = self.modes[row];
    return key;
    
}

- (void)pickerView:(UIPickerView *)pickerView
      didSelectRow:(NSInteger)row
       inComponent:(NSInteger)component
{
    [self setDartMode: (int)row];
    [self playSelection];
}

// set the dart mode
- (void)setDartMode:(int)mode
{
    UInt8 buf[3] = {0x02, 0x00, 0x00};      // prepare command
    buf[2] = (Byte) mode;
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
}

- (void)playSelection
{
    // send stop command
    [self stopAction:self.stopButton];
    
    // send play command
    [self playAction:self.playButton];
    
}

#pragma mark - brightness slider methods

- (IBAction)BrightnessSliderAction:(UISlider *)sender
{
    self.brightness = (int)sender.value;
    [self writeBLEBrightness: (int)sender.value];
}

- (void) writeBLEBrightness: (int)value
{
    UInt8 buf[3] = {0x0F, 0x00, 0x00};      // prepare command
    buf[2] = (Byte) value;
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
}

#pragma mark - BLE LED-Bot Methods
// write red/green values - all values are converted to RGB from HSI
- (void) writeBLE_RG
{
    UInt8 buf[3] = {0x0f, 0x00, 0x00};      // prepare command
    buf[0] = [self getCommand];
    buf[1] = (Byte)self.activeConfig.red;
    buf[2] = (Byte)self.activeConfig.green;
    
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
    printf("%s: 0x%02X, 0x%02X, 0x%02X\n", [[self byteToCommand:buf[0]] UTF8String],
           buf[0], buf[1], buf[2]);
    [self writeBLE_AllOn];
    
}

- (void) writeBLE_B
{
    UInt8 buf[3] = {0x0f, 0x00, 0x00};      // prepare command
    buf[0] = [self getCommand] + 1;
    buf[2] = (Byte)self.activeConfig.blue;
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
    printf("%s: 0x%02X, 0x%02X, 0x%02X\n", [[self byteToCommand:buf[0]] UTF8String],
           buf[0], buf[1], buf[2]);
    [self writeBLE_AllOn];
    
}


-(void)writeBLE_AllOn
{
    UInt8 buf[3] = {0x02, 0x00, 0x07};      // set mode to 7
    NSData *data = [[NSData alloc] initWithBytes:buf length:3];
    [self.ble write:data];
    printf("%s: 0x%02X, 0x%02X, 0x%02X\n", [[self byteToCommand:buf[0]] UTF8String],
           buf[0], buf[1], buf[2]);
    
    buf[0] = 0x01;      // stop/play/reset command
    buf[2] = 0x01;      // play
    buf[1] = (Byte) self.selectedMode;  // select the dart color configuration index
    data = [[NSData alloc] initWithBytes:buf length:3];
    
    [self.ble write:data];
    printf("%s: 0x%02X, 0x%02X, 0x%02X\n", [[self byteToCommand:buf[0]] UTF8String],
           buf[0], buf[1], buf[2]);
}

- (int)getIndexFromLastConfig
{
    int index = 0;
    for (LED *ledCfg in self.ledConfigs.configs) {
        if ([ledCfg isEqual:self.ledConfigs.lastConfig])
            break;
        index++;
    }
    self.selectedMode = index;
    return index;
}

- (Byte)getCommand
{
    
    // RGB Mode
    switch (self.selectedMode) {
        case 0: // dart1
            return 0x03;
            break;
        case 1: // dart2
            return 0x05;
            break;
        case 2: // dart3
            return 0x07;
            break;
        case 3: // dart4
            return 0x09;
            break;
        case 4: // dart5
            return 0x0b;
            break;
        case 5: // background
            return 0x0d;
            break;
            
        default:
            return 0;
            break;
    }
}

#pragma mark - helper methods
// this pops the number of view controllers indicated
- (void) popControllersNumber:(int)number
{
    if (number <= 1)
        [[self navigationController] popViewControllerAnimated:YES];
    else
    {
        NSArray* controller = [[self navigationController] viewControllers];
        int requiredIndex = (int)[controller count] - number - 1;
        if (requiredIndex < 0) requiredIndex = 0;
        UIViewController* requireController = [[[self navigationController]
                                                viewControllers] objectAtIndex:requiredIndex];
        [[self navigationController] popToViewController:requireController animated:YES];
    }
}

// if not in the middle of a test (self.configEnabled == YES), then
- (IBAction)configButton:(UIBarButtonItem *)sender
{
    if (self.configEnabled) {
        [self performSegueWithIdentifier:@"Configure" sender:self];
    }
}

- (void)prepareForSegue:(UIStoryboardSegue *)segue sender:(id)sender {
    
    if ([segue.identifier isEqualToString:@"Configure"]) {
        ConfigVC *vc = [segue destinationViewController];    // called once connected
        // send stop command
        [self stopAction:self.stopButton];
        
        vc.ble = self.ble;          // set the BLE object
        vc.ledConfigs = self.ledConfigs;  //
    }
}

@end
