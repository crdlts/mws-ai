import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
} from '@angular/forms';

@Component({
  standalone: true,
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.less'],
  imports: [CommonModule, ReactiveFormsModule],
})
export class RegisterComponent {
  form: FormGroup;
  isSubmitting = false;

  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required, Validators.minLength(8)]],
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Проверка совпадения паролей
    const { password, confirmPassword } = this.form.value;
    if (password !== confirmPassword) {
      // Здесь можно добавить ошибку в форму
      console.log('Passwords do not match');
      return;
    }

    this.isSubmitting = true;

    // TODO: сюда воткнёшь реальный AuthService
    console.log('Register payload:', this.form.value);

    // имитация завершения
    setTimeout(() => {
      this.isSubmitting = false;
    }, 700);
  }
}
