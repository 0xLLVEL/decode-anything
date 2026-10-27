<?php

namespace SpondonIt\Service\Requests;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Requests\LicenseRequest.php
 */

class LicenseRequest extends Illuminate\Foundation\Http\FormRequest {
    public function authorize(): bool {
        return true;
    }

    public function rules(): array {
        return ['access_code' => 'required', 'envato_email' => 'required|email'];
    }

    public function attributes(): array {
        return [
            'access_code' => trans('service::install.access_code'),
            'envato_email' => trans('service::install.envato_email'),
        ];
        return null;
    }
}
