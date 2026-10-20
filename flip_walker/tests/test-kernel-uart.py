#!/usr/bin/env python3
"""Execute the actual staged driver functions with mocked kernel callbacks."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1]
source=(r.parent/'native/kyf37-android11/kernel/kyocera/kyf37/drivers/felica/kfelica.c').read_text()
def section(start,end):
    a=source.index(start);b=source.index(end,a);return source[a:b]
functions=section('static int felicadev_open(struct inode *inode, struct file *file)\n{','\nstatic int felicadev_release(')
functions+=section('static ssize_t ue_write(struct file *file, const char __user *data, size_t len, loff_t *ppos)\n{','\nstatic int ue_init(void)')
header=r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sys/types.h>
#include <errno.h>
#define __user
#define ERESTARTSYS 512
struct inode { int n; };
struct file { int n; };
struct icc_poll_data { int rsp_wait, rsp_done; } g_felicadev_data;
static char g_ue_data,g_felica_open,g_carbuf[16];
static struct file *g_ue_owner;
static int g_felicadev_open_cnt,g_flcsts,g_functype,g_startkind;
static int chardev_sem, depth, wait_result, conflict, checks;
static void require(bool ok,const char *name){if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}checks++;printf("PASS %s\n",name);}
static int down_interruptible(int *s){(void)s;if(++depth!=1)abort();return 0;}
static void down(int *s){(void)down_interruptible(s);}
static void up(int *s){(void)s;if(depth--!=1)abort();}
static int felicadev_chk_conflict(void){return conflict;}
static void felicadev_poll_kick(void){}
static int copy_from_user(void *to,const void *from,size_t n){memcpy(to,from,n);return 0;}
#define wait_event_interruptible_timeout(q,condition,ticks) (wait_result)
static void reset(void){g_ue_data=0;g_felica_open=0;g_ue_owner=NULL;g_felicadev_open_cnt=0;g_flcsts=0;g_functype=-1;g_startkind=255;g_felicadev_data.rsp_done=0;memset(g_carbuf,0,sizeof(g_carbuf));wait_result=1;conflict=0;depth=0;}
'''
main=r'''
int main(void){
 struct file a={1},b={2};reset();
 require(ue_open(NULL,&a)==0,"lease device opens without claiming");
 wait_result=0;
 require(felicadev_open(NULL,&a)==-ETIMEDOUT && !g_felica_open && depth==0,"missing FeliCa daemon times out and frees ownership");
 require(ue_ioctl(&a,0x4bf0,0)==0 && g_ue_owner==&a && g_ue_data==1,"atomic IR claim after failed FeliCa open");
 require(felicadev_open(NULL,&b)==-EBUSY && g_ue_owner==&a,"FeliCa cannot enter while IR owns UART");
 require(ue_ioctl(&b,0x4bf1,0)==-EPERM && g_ue_owner==&a,"foreign descriptor cannot release IR lease");
 char zero=0;
 require(ue_write(&b,&zero,1,NULL)==-EBUSY && g_ue_data==1,"legacy writer cannot release another descriptor's lease");
 require(ue_release(NULL,&b)==0 && g_ue_owner==&a,"closing unrelated descriptor preserves lease");
 require(ue_release(NULL,&a)==0 && !g_ue_owner && !g_ue_data,"process exit automatically releases IR lease");
 reset();wait_result=-ERESTARTSYS;
 require(felicadev_open(NULL,&a)==-ERESTARTSYS && !g_felica_open && depth==0,"interrupted FeliCa open frees ownership");
 reset();g_startkind=1;wait_result=0;
 require(felicadev_open(NULL,&a)==-ETIMEDOUT && !g_felica_open && depth==0,"poll-phase timeout reacquires lock for cleanup");
 reset();
 require(felicadev_open(NULL,&a)==0 && g_felica_open && g_felicadev_open_cnt==1,"successful FeliCa open retains ownership");
 require(ue_ioctl(&b,0x4bf0,0)==-EBUSY,"IR claim refuses a successful FeliCa open");
 reset();g_felica_open=1;g_functype=7;
 require(felicadev_open(NULL,&b)==-EBUSY && g_felica_open && g_functype==7,"second failed open cannot clear pending owner's state");
 reset();g_carbuf[1]=1;
 require(felicadev_open(NULL,&a)==-EIO && !g_felica_open,"negative daemon response frees ownership");
 reset();conflict=-EIO;
 require(felicadev_open(NULL,&a)==-EIO && !g_felica_open,"conflict path does not reserve UART");
 require(ue_ioctl(&a,0,0)==-ENOTTY && !g_ue_data,"unsupported ioctl leaves ownership untouched");
 printf("KERNEL_UART_CHECKS=%d\n",checks);return 0;
}
'''
out=r/'build/kernel-tests';out.mkdir(parents=True,exist_ok=True)
(out/'uart_test.c').write_text(header+functions+main)
subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(out/'uart_test.c'),'-o',str(out/'uart_test')],check=True)
subprocess.run([str(out/'uart_test')],check=True)
