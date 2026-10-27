<?php

namespace SpondonIt\Service\Requests;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Requests\DatabaseRequest.php
 */

class DatabaseRequest extends Illuminate\Foundation\Http\FormRequest {
    public function authorize(): bool {
        return true;
    }

    public function rules(): array {
        $rules = [
            'db_port' => 'required',
            'db_host' => 'required',
            'db_database' => 'required',
            'db_username' => 'required',
        ];
        if (config('spondonit.support_multi_connection', false)) {
            $rules += ['db_connection' => 'required|in:mysql,pgsql'];
        }
        return $rules;
    }

    public function attributes(): array {
        return [
            'db_connection' => trans('service::install.db_connection'),
            'db_port' => trans('service::install.db_port'),
            'db_host' => trans('service::install.db_host'),
            'db_database' => trans('service::install.db_database'),
            'db_username' => trans('service::install.db_username'),
        ];
        return null;
    }
}
