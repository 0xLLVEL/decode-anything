<?php

namespace SpondonIt\Service\Requests;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Requests\ThemeInstallRequest.php
 */

class ThemeInstallRequest extends Illuminate\Foundation\Http\FormRequest {
    public function authorize(): bool {
        return true;
    }

    public function rules(): array {
        return [
            'purchase_code' => 'required',
            'name' => 'required',
            'envatouser' => 'required|email',
        ];
        return null;
    }

    public function attributes(): array {
        return [
            'purchase_code' => trans('service::install.purchase_code'),
            'name' => trans('service::install.theme_name'),
            'envatouser' => trans('service::install.envatouser'),
        ];
        return null;
    }
}
