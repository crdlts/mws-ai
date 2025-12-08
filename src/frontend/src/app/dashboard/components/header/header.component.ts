import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.less'],
  standalone: true,
  imports: [RouterLink],
})
export class HeaderComponent {
  isUserPanelOpen = false;
  isSearchPanelOpen = false;
  isKioskMode = false;
  isKioskNotificationVisible = false;
  private kioskNotificationTimeout: any;

  @ViewChild('userPanel') userPanel!: ElementRef;
  @ViewChild('userDropdownToggle') userDropdownToggle!: ElementRef;
  @ViewChild('searchModal') searchModal!: ElementRef;

  constructor() {}

  toggleUserPanel(): void {
    this.isUserPanelOpen = !this.isUserPanelOpen;
  }

  openSearchPanel(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.isSearchPanelOpen = true;
  }

  closeSearchPanel(): void {
    this.isSearchPanelOpen = false;
  }

  toggleKioskMode(): void {
    this.isKioskMode = !this.isKioskMode;
    
    if (this.isKioskMode) {
      // Enter kiosk mode
      // Notification will be shown after a short delay to ensure kiosk mode is fully activated
      setTimeout(() => {
        this.showKioskNotification();
      }, 100);
    } else {
      // Exit kiosk mode
      this.hideKioskNotification();
    }
  }

  showKioskNotification(): void {
    // Clear any existing timeout
    if (this.kioskNotificationTimeout) {
      clearTimeout(this.kioskNotificationTimeout);
    }
    
    // Show the notification
    this.isKioskNotificationVisible = true;
    
    // Hide the notification after 3 seconds
    this.kioskNotificationTimeout = setTimeout(() => {
      this.hideKioskNotification();
    }, 3000);
  }

  hideKioskNotification(): void {
    this.isKioskNotificationVisible = false;
    
    // Clear any existing timeout
    if (this.kioskNotificationTimeout) {
      clearTimeout(this.kioskNotificationTimeout);
      this.kioskNotificationTimeout = null;
    }
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    // Close search panel if window is resized to prevent layout issues
    if (this.isSearchPanelOpen) {
      this.closeSearchPanel();
    }
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event): void {
    // Handle user panel click outside
    if (this.isUserPanelOpen) {
      const clickedInsideUserPanel = this.userPanel?.nativeElement.contains(
        event.target
      );
      const clickedInsideUserToggle =
        this.userDropdownToggle?.nativeElement.contains(event.target);

      if (!clickedInsideUserPanel && !clickedInsideUserToggle) {
        this.isUserPanelOpen = false;
      }
    }

    // Handle search panel click outside
    if (this.isSearchPanelOpen) {
      const searchContainer = document.querySelector('.search-container');
      const clickedInsideSearchContainer = 
        searchContainer && event.target instanceof Node && 
        searchContainer.contains(event.target);

      // Close search panel if click is outside the entire search container
      if (!clickedInsideSearchContainer) {
        this.closeSearchPanel();
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.isSearchPanelOpen) {
      this.closeSearchPanel();
    }
    
    // Exit kiosk mode if active
    if (this.isKioskMode) {
      this.toggleKioskMode();
    }
    
    // Hide kiosk notification if visible
    if (this.isKioskNotificationVisible) {
      this.hideKioskNotification();
    }
  }
}
