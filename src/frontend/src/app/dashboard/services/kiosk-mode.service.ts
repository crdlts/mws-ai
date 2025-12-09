import { Injectable, signal } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class KioskModeService {
  isKioskMode = signal(false);
  isKioskNotificationVisible = signal(false);
  private kioskNotificationTimeout: any;

  // Subjects for communication
  kioskModeToggled = new Subject<boolean>();
  showNotification = new Subject<void>();
  hideNotification = new Subject<void>();

  enable() {
    this.isKioskMode.set(true);
    this.kioskModeToggled.next(true);
    
    // Show notification after a short delay
    setTimeout(() => {
      this.showKioskNotification();
    }, 100);
  }

  disable() {
    this.isKioskMode.set(false);
    this.kioskModeToggled.next(false);
    this.hideKioskNotification();
  }

  toggle() {
    if (this.isKioskMode()) {
      this.disable();
    } else {
      this.enable();
    }
  }

  showKioskNotification(): void {
    // Clear any existing timeout
    if (this.kioskNotificationTimeout) {
      clearTimeout(this.kioskNotificationTimeout);
    }
    
    // Show the notification
    this.isKioskNotificationVisible.set(true);
    this.showNotification.next();
    
    // Hide the notification after 3 seconds
    this.kioskNotificationTimeout = setTimeout(() => {
      this.hideKioskNotification();
    }, 3000);
  }

  hideKioskNotification(): void {
    this.isKioskNotificationVisible.set(false);
    this.hideNotification.next();
    
    // Clear any existing timeout
    if (this.kioskNotificationTimeout) {
      clearTimeout(this.kioskNotificationTimeout);
      this.kioskNotificationTimeout = null;
    }
  }
}
