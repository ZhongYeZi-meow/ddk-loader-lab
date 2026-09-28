// SPDX-License-Identifier: GPL-2.0-only
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/printk.h>

/* All state belongs to this module; there are no hooks or background tasks. */
static unsigned int cookie = 20260928;
static bool fail_init;
static bool ready;

module_param(cookie, uint, 0400);
MODULE_PARM_DESC(cookie, "Read-only value for verifying module parameter delivery");
module_param(fail_init, bool, 0400);
MODULE_PARM_DESC(fail_init, "Return EINVAL before initialization for failure-path testing");
module_param(ready, bool, 0400);
MODULE_PARM_DESC(ready, "True after successful initialization");

static int __init kh_loader_smoke_init(void)
{
	ready = false;
	if (fail_init) {
		pr_info("kh_loader_smoke: requested initialization failure\n");
		return -EINVAL;
	}
	ready = true;
	pr_info("kh_loader_smoke: ready cookie=%u\n", cookie);
	return 0;
}

static void __exit kh_loader_smoke_exit(void)
{
	ready = false;
	pr_info("kh_loader_smoke: unloaded cookie=%u\n", cookie);
}

module_init(kh_loader_smoke_init);
module_exit(kh_loader_smoke_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("ddk-loader-lab contributors");
MODULE_DESCRIPTION("Minimal module loading and parameter smoke test");
MODULE_VERSION("1.0.0");
