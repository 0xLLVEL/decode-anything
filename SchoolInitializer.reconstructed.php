<?php

namespace SpondonIt\SchoolService\Initializers;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * SchoolInitializer.php
 */

class SchoolInitializer implements SpondonIt\Service\Contracts\AppInitializerInterface {
    public function init(): void {
        config(['app.item' => config('school.item_id')]);
    }

    public function config(): void {
        app()->singleton('permission', function () {
            if (!Illuminate\Support\Facades\Auth::check()) {
                return [];
            }
            $infixRole = Modules\RolePermission\Entities\InfixRole::find(Illuminate\Support\Facades\Auth::user()->role_id);
            $permissionIds = Modules\RolePermission\Entities\AssignPermission::where('role_id', Illuminate\Support\Facades\Auth::user()->role_id)->when($infixRole->is_saas == 0, function ($q) {
                $q->where('school_id', Illuminate\Support\Facades\Auth::user()->school_id);
            })->pluck('permission_id')->toArray();
            return Modules\RolePermission\Entities\Permission::whereIn('id', $permissionIds)->pluck('route')->toArray();
        });
    }
}
