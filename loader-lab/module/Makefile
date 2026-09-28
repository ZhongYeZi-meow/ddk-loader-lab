ifneq ($(KERNELRELEASE),)
obj-m := kh_loader_smoke.o
else
MODULE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
.PHONY: all clean
all:
	@test -n "$(KDIR)" || { echo "KDIR must point to a prepared DDK kernel build"; exit 1; }
	$(MAKE) -C "$(KDIR)" M="$(MODULE_DIR)" modules
clean:
	@test -n "$(KDIR)"
	$(MAKE) -C "$(KDIR)" M="$(MODULE_DIR)" clean
endif
