<?php

namespace SpondonIt\Service\Controllers;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Controllers\LicenseController.php
 */

class LicenseController extends Illuminate\Routing\Controller {
    protected $licenseService;
    protected $installService;
    protected $request;

    public function __construct($licenseService, $installService, $request) {
        $this->licenseService = $licenseService;
        $this->installService = $installService;
        $this->request = $request;
        $this->middleware('auth');
    }

    public function revoke() {
        $ac = Illuminate\Support\Facades\Storage::exists('.app_installed') ? Illuminate\Support\Facades\Storage::get('.app_installed') : null;
        if (!$ac) {
            return redirect()->route('service.install');
        }
        $this->licenseService->revoke();
        return redirect()->route('service.install');
    }

    public function installModule($request) {
        try {
            $response = $this->installService->installModule($request->validated());
        } catch (\Exception $e) {
            return response()->json(['message' => $e->getMessage()], 422);
        }
        return response()->json([
            'message' => trans('service::install.module_verify'),
            'response' => $response,
        ]);
    }

    public function revokeModule($request) {
        try {
            $response = $this->installService->revokeModule($request->all());
        } catch (\Exception $e) {
            return response()->json(['message' => $e->getMessage()], 422);
        }
        return response()->json([
            'message' => __('Module license revoked successfully.'),
            'response' => $response,
        ]);
    }

    public function installTheme($request) {
        try {
            $response = $this->installService->installTheme($request->validated());
        } catch (\Exception $e) {
            return response()->json(['message' => $e->getMessage()], 422);
        }
        return response()->json([
            'message' => trans('service::install.theme_verify'),
            'response' => $response,
        ]);
    }

    public function revokeTheme($request) {
        try {
            $response = $this->installService->revokeTheme($request->all());
        } catch (\Exception $e) {
            return response()->json(['message' => $e->getMessage()], 422);
        }
        return response()->json([
            'message' => __('Theme license revoked successfully.'),
            'response' => $response,
        ]);
    }
}
