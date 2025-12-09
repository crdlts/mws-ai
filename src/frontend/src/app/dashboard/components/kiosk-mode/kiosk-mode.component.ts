import { Component, inject, HostListener } from '@angular/core';
import { KioskModeService } from '../../services/kiosk-mode.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-kiosk-mode',
  templateUrl: './kiosk-mode.component.html',
  styleUrls: ['./kiosk-mode.component.less'],
  standalone: true,
  imports: [CommonModule]
})
export class KioskModeComponent {
  kioskModeService = inject(KioskModeService);
  
  constructor() { }
  
  hideKioskNotification(): void {
    this.kioskModeService.hideKioskNotification();
  }
  
  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    // Exit kiosk mode if active
    if (this.kioskModeService.isKioskMode()) {
      this.kioskModeService.toggle();
    }
    
    // Hide kiosk notification if visible
    if (this.kioskModeService.isKioskNotificationVisible()) {
      this.kioskModeService.hideKioskNotification();
    }
  }
}
