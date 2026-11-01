/*
  +----------------------------------------------------------------------+
  | PHP Version 7 - opcodedump extension (PHP 7.2 build)                |
  +----------------------------------------------------------------------+
*/

#ifndef PHP_OPCODEDUMP_H
#define PHP_OPCODEDUMP_H

extern zend_module_entry opcodedump_module_entry;
#define phpext_opcodedump_ptr &opcodedump_module_entry

#define PHP_OPCODEDUMP_VERSION "0.1.0"

#ifdef PHP_WIN32
#	define PHP_OPCODEDUMP_API __declspec(dllexport)
#elif defined(__GNUC__) && __GNUC__ >= 4
#	define PHP_OPCODEDUMP_API __attribute__ ((visibility("default")))
#else
#	define PHP_OPCODEDUMP_API
#endif

#ifdef ZTS
#include "TSRM.h"
#endif

#define OPCODEDUMP_G(v) ZEND_MODULE_GLOBALS_ACCESSOR(opcodedump, v)

#if defined(ZTS) && defined(COMPILE_DL_OPCODEDUMP)
ZEND_TSRMLS_CACHE_EXTERN()
#endif

/* PHP 7.0 */
#if (PHP_MAJOR_VERSION == 7 && PHP_MINOR_VERSION == 0)
# define ZEND_ENGINE_7_0
#endif

/* PHP 7.1 and later (includes 7.2, 7.3 …) */
#if (PHP_MAJOR_VERSION == 7 && PHP_MINOR_VERSION >= 1)
# define ZEND_ENGINE_7_1
#endif

#endif /* PHP_OPCODEDUMP_H */

/*
 * Local variables:
 * tab-width: 4
 * c-basic-offset: 4
 * End:
 */
