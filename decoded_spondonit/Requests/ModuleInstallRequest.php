<?php

namespace SpondonIt\Service\Requests;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Requests\ModuleInstallRequest.php
 */

class ModuleInstallRequest extends Illuminate\Foundation\Http\FormRequest {
    public function authorize(): bool {
        return true;
    }

    public function rules(): array {
        return [
            'purchase_code' => 'required',
            'name' => 'required',
            'envatouser' => 'required|email',
            'row' => 'nullable',
        ];
        return null;
    }

    public function attributes(): array {
        return [
            'purchase_code' => trans('service::install.purchase_code'),
            'name' => trans('service::install.module_name'),
            'envatouser' => trans('service::install.envatouser'),
        ];
        return null;
    }
}
