<?php

namespace SpondonIt\Service\Controllers\Api;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * C:\Users\ezan\Documents\ioncube\vendor\spondonit\service\src\Controllers\Api\VerifyController.php
 */

class VerifyController extends Illuminate\Routing\Controller {
    private $initService;
    private $request;

    public function __construct($initService, $request) {
        $this->initService = $initService;
        $this->request = $request;
    }

    public function index() {
        if (!$this->request->wantsJson()) {
            return 'invalid api call';
        }
        return response()->json($this->initService->dailyApiCheck());
    }
}
