import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.less'],
  standalone: true,
  imports: [RouterLink]
})
export class HeaderComponent {
  isUserPanelOpen = false;
  isSearchPanelOpen = false;

  @ViewChild('userPanel') userPanel!: ElementRef;
  @ViewChild('userDropdownToggle') userDropdownToggle!: ElementRef;
  @ViewChild('searchModal') searchModal!: ElementRef;

  constructor() { }

  toggleUserPanel(): void {
    this.isUserPanelOpen = !this.isUserPanelOpen;
  }

  openSearchPanel(): void {
    this.isSearchPanelOpen = true;
  }

  closeSearchPanel(): void {
    this.isSearchPanelOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event): void {
    // Handle user panel click outside
    if (this.isUserPanelOpen) {
      const clickedInsideUserPanel = this.userPanel?.nativeElement.contains(event.target);
      const clickedInsideUserToggle = this.userDropdownToggle?.nativeElement.contains(event.target);

      if (!clickedInsideUserPanel && !clickedInsideUserToggle) {
        this.isUserPanelOpen = false;
      }
    }

    // Handle search panel click outside
    if (this.isSearchPanelOpen) {
      const clickedInsideSearchDropdown = this.searchModal?.nativeElement.contains(event.target);
      const clickedOnSearchInput = event.target instanceof Element && 
        event.target.closest('.search-input-wrapper') !== null;

      // Close search panel if click is outside dropdown and not on search input
      if (!clickedInsideSearchDropdown && !clickedOnSearchInput) {
        this.closeSearchPanel();
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.isSearchPanelOpen) {
      this.closeSearchPanel();
    }
  }
}
