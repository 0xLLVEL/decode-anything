<?php

namespace SpondonIt\Service\Requests;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Requests\UserRequest.php
 */

class UserRequest extends Illuminate\Foundation\Http\FormRequest {
    public function authorize(): bool {
        return true;
    }

    public function rules(): array {
        return [
            'email' => 'required|email',
            'password' => 'required|min:8',
            'password_confirmation' => 'required|same:password',
        ];
        return null;
    }

    public function attributes(): array {
        return [
            'email' => trans('service::install.email'),
            'password' => trans('service::install.password'),
            'password_confirmation' => trans('service::install.password_confirmation'),
        ];
        return null;
    }

    public function messages(): array {
        return [
            'password.min' => trans('service::install.the_password_must_be_at_least_8_characters'),
        ];
        return null;
    }
}
