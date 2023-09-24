//
//  LEDBotTVC.h
//  Fin6LEDBot
//
//  Created by jim kardach on 8/26/16.
//  Copyright © 2016 Forkbeardlabs. All rights reserved.
//

#import <UIKit/UIKit.h>
#include "BLE.h"
#include "DartConfig.h"

@interface LEDBotTVC : UITableViewController
@property (strong, nonatomic) BLE *ble;
@property (strong, nonatomic) DartConfig *ledConfigs;
@end
