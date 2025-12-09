import { Component, inject } from '@angular/core';
import { HeaderComponent } from '../header/header.component';
import { KioskModeService } from '../../services/kiosk-mode.service';
import { KioskModeComponent } from '../kiosk-mode/kiosk-mode.component';

@Component({
  selector: 'app-main-page',
  templateUrl: './main-page.component.html',
  styleUrls: ['./main-page.component.less'],
  imports: [HeaderComponent, KioskModeComponent],
})
export class MainPageComponent {
  kioskModeService = inject(KioskModeService);

  constructor() {}
}
