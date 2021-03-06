#!/usr/bin/python
#    "$Name:  $";
#    "$Header:  $";
#=============================================================================
#
# file :        ProcessProfiler.py
#
# description : Python source for the ProcessProfiler and its commands. 
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                ProcessProfiler are implemented in this file.
#
# project :     TANGO Device Server
#
# $Author:  $
#
# $Revision:  $
#
# $Log:  $
#
# copyleft :    European Synchrotron Radiation Facility
#               BP 220, Grenoble 38043
#               FRANCE
#
#=============================================================================
#          This file is generated by POGO
#    (Program Obviously used to Generate tango Object)
#
#         (c) - Software Engineering Group - ESRF
#=============================================================================
#


import PyTango
import sys,os,traceback,re,time
#from multiprocessing import cpu_count#,Process
#import threading

import fandango as fn
from fandango.linos import shell_command,get_process_pid,get_memory #,get_cpu,get_memory

if 'PyDeviceClass' not in dir(PyTango): PyTango.PyDeviceClass = PyTango.DeviceClass

__doc__ = """
    ProcessProfiler Usage
    ---------------------
    
    # Create a new device ; preferably like sys/profile/${HOSTNAME}
    # Configure the properties with the list of processes to control:
    
    .. note: ProcessList:
                Starter
                notifd
                ProcessProfiler
      
    A sample code to do so would be::

        import fandango
        host = fn.linos.MyMachine().host
        #Create the device
        fn.tango.add_new_device('ProcessProfiler/%s'%host,'ProcessProfiler','sys/profile/%s'%host)
        #Setup properties
        fn.get_database().put_device_property('sys/profile/%s'%host,{'ProcessList':['Starter','notifd','ProcessProfiler']})
        #Start the device
        fn.Astor('sys/profile/%s'%host).start_servers(host=host)
        #Start the update() command polling
        time.sleep(15.)
        fn.get_device(sys/profile/%s'%host).poll_command('update',10000)
    """

#def get_nthreads(process_pid):
#    comm = "ps -ef |grep %d|grep -v grep |awk '{print $4}'"%process_pid
#    threads_list = shell_command(comm).split('\n')
#    return len(threads_list)
#
#def get_cpu(pid):
#    """ Uses ps to get the CPU usage of a process by PID ; it will trigger exception of PID doesn't exist """
#    comm = 'ps h -p %d -o pcpu'%pid
#    cpu = shell_command(comm)
#    return float(cpu)
#def get_memory(pid):
#    comm = 'ps h -p %d -o size'%pid
#    cpu = shell_command(comm)
#    return float(cpu)/1000 #MB

#def get_threads_cpu_and_memory(pid):
    #try:
        #comm = 'ps h -p %d -o nlwp,%%cpu,%%mem,rss,vsize'%pid
        #bar = filter(bool,shell_command(comm).strip().split(' '))
        #nthreads,cpu,memRatio,mem,vmem = bar
        #return [int(nthreads),float(cpu),float(memRatio),float(mem)/1000.,float(vmem)/1000.] #MB
    #except:
        #return 0,float('nan'),float('nan'),float('nan'),float('nan')

#def get_processes_pid(process_name):
    #try:
        #comm = "ps -ef |grep '%s'|grep -v grep |awk '{print $2}'"%process_name
        #process_list = shell_command(comm)
        #if process_list == None: return []
        #return [int(p) for p in process_list.split('\n') if p.strip()]
    #except:
        #return []
        
def tracer(msg):
    print('%s: %s'%(fn.time2str(),msg))
        
def memory_checker(f):
    def wrapper(*args,**kwargs):
        m0 = get_memory()
        v = f(*args,**kwargs)
        m = get_memory()
        diff = m-m0
        if diff>0: 
            print 'In %s: '%f.__name__ + '%s: + %s'%(m*1e-6, (m-m0)*1e-6)
        return v
    return wrapper
        
@memory_checker
def get_all_process(regexp=''):
    """
    Returns a {int(PID):stats} dictionary
    """
    import re
    #tracer('get_all_process(%s)'%regexp)
    pss = {}
    try:
        comm = "ps hax -o pid,nlwp,%cpu,%mem,rss,vsize,cmd"#hax is needed to show Starter process
        lines = shell_command(comm).split('\n')
        for r in map(str.split,lines):
            if not r: continue
            r = dict((k,v if k=='cmd' else (float(v) if '.' in v else int(v))) for k,v in zip(('pid','threads','cpu','mem','rss','vsize','cmd'),(r[0:6])+[' '.join(r[6:])]))
            #r['rss'],r['vsize'] = 1e-3*r['rss'],1e-3*r['vsize'] #Memory read in MB
            r['rss'],r['vsize'] = r['rss'],r['vsize'] #Memory read in KBytes
            if r['pid'] and not regexp or re.search(regexp,r.get('cmd','')):
                pss[int(r['pid'])] = r
    except:
        print(traceback.format_exc())
    return pss
            
def get_worse_process(processes=None,key='rss'):
    # processes must be {PID:dict} 
    all_proc = processes or get_all_process()
    return sorted((v[key],v['pid']) for v in all_proc.values())[-1][-1]
    
def getMemUsage(pid=None,virtual=False):    
    """
    DEPRECATED, GET IT FROM self.all_proc
    """
    tracer('getMemUsage(%s)'%pid)
    if pid is None: pid = self._PID
    tag = 'Vm%s'%('Size' if virtual else 'RSS')
    #mem,units = shell_command('cat /proc/%s/status | grep Vm%s'%(pid,'Size' if virtual else 'RSS')).lower().strip().split()[1:3]
    f = open('/proc/%s/status'%pid,'r')
    lines = f.readlines()
    f.close()
    l = (a for a in lines if tag in a).next()
    mem,units = l.lower().strip().split()[1:3]
    mem = int(mem)*(1e3 if 'k' in units else (1e6 if 'm' in units else 1))
    del lines
    return mem

class ProcessProfiler(PyTango.Device_4Impl):

    #--------- Add you global variables here --------------------------
    
    def getMemRate(self):
        try:
            #print('getMemRate()')
            meminfo = shell_command('cat /proc/meminfo').split('\n')
            meminfo = dict(map(str.strip,a.split(':',1)) for a in meminfo if a.strip())
            getter = lambda k: float(eval(meminfo[k].lower().replace('kb','*1').replace('mb','*1e3').replace('b','*1e-3')))
            self._total, self._free, self._cached = getter('MemTotal'),getter('MemFree'),getter('Cached')
            self._cached += getter('Slab') + getter('Buffers')
            ## Shared Memory Reclaimable could be considered also as Cached, but it is not 100% sure if it will be always reusable or not
            # Therefore, I prefered to ignore it. This is why this method may return less free memory than top.
            self._used = (self._total-(self._free+self._cached))
            self._memrate = (self._used/self._total)
        except:
            traceback.print_exc()
            self._memrate = 0.
        return self._memrate

    def fireEventsList(self,eventsAttrList):
        #self.debug_stream("In %s::fireEventsList()"%self.get_name())
        #@todo: add the value on the push_event

        timestamp = time.time()
        for attrEvent in eventsAttrList:
            try:
                #self.debug_stream("In %s::fireEventsList() attribute: %s"%(self.get_name(),attrEvent[0]))
                if len(attrEvent) == 3:#specifies quality
                    self.push_change_event(attrEvent[0],attrEvent[1],
                                    timestamp,attrEvent[2])
                else:
                    self.push_change_event(attrEvent[0],attrEvent[1],
                                    timestamp,PyTango.AttrQuality.ATTR_VALID)
            except Exception,e:
                self.error_stream("In %s::fireEventsList() Exception with attribute %s"%(self.get_name(),attrEvent[0]))
                print e

    def change_state(self,newstate):
        #self.debug_stream("In %s::change_state(%s)"%(self.get_name(),str(newstate)))
        if self.get_state != newstate:
            self.set_state(newstate)
            if self.UseEvents:self.push_change_event('State',newstate)

    @memory_checker
    def addStatusMsg(self,current,important = False):
        #self.debug_stream("In %s::addStatusMsg()"%self.get_name())
        msg = "The device is in %s state.\n"%(self.get_state())
        for ilog in self._important_logs:
            msg = "%s%s\n"%(msg,ilog)
        status = "%s%s\n"%(msg,current)
        if self.get_status() != status:
            self.set_status(status)
            if self.UseEvents:self.push_change_event('Status',status)
        if important and not current in self._important_logs:
            self.info_stream('writing logs ...')
            self._important_logs.append(current)

    @memory_checker
    def _read_dyn_attr(self,attr):
        aname = attr.get_name()
        tracer('read_dyn_attr(%s)'%aname)
        value = self.values.get(aname,None)
        self.debug_stream('In read_dyn_attr(%s) = %s ; (mem = %s)'%(aname,value,get_memory()))
        if value == None:
            attr.set_quality(PyTango.AttrQuality.ATTR_INVALID)
        elif attr.get_data_format() == PyTango.SCALAR:
            attr.set_value(value)
        elif attr.get_data_format() == PyTango.SPECTRUM:
            attr.set_value(value,len(value))
            
    def read_dyn_attr(self,attr): self._read_dyn_attr(attr)
    
    #need by new way to read dynamic attributes
    if getattr(PyTango,'__version_number__',0)<722:
        read_dyn_attr=staticmethod(read_dyn_attr)
      
    #Needed to have proper dynamic attributes
    @memory_checker
    def dyn_attr(self):
        for process in self.ProcessList:
            #self.debug_stream('dyn_attr(): Adding attributes for %s process'%process)
            aname = re.sub('[^0-9a-zA-Z]+','_',process)
            for suffix,data_type,data_format,unit in\
                (('nprocesses',PyTango.DevLong,PyTango.SCALAR,None),
                 ('nthreads',PyTango.DevLong,PyTango.SCALAR,None),
                 ('pids',PyTango.DevLong,PyTango.SPECTRUM,None),
                 ('cpu',PyTango.DevDouble,PyTango.SCALAR,'%'),
                 ('mem',PyTango.DevDouble,PyTango.SCALAR,'MB'),
                 ('vmem',PyTango.DevDouble,PyTango.SCALAR,'MB'),
                 ('memRatio',PyTango.DevDouble,PyTango.SCALAR,'%'),
                 ('kbpm',PyTango.DevDouble,PyTango.SCALAR,'%'),
                ):
                #TODO: set the units
                if data_format == PyTango.SCALAR:
                    self.add_attribute(PyTango.Attr(aname+'_'+suffix,
                                                    data_type,
                                                    PyTango.AttrWriteType.READ),
                                       self.read_dyn_attr,None,
                                       (lambda s,req_type,attr_name=aname+'_'+suffix: True))
                    if self.UseEvents: 
                        self.set_change_event(aname+'_'+suffix, True, False)

                elif data_format == PyTango.SPECTRUM:
                    self.add_attribute(PyTango.SpectrumAttr(aname+'_'+suffix,
                                                            data_type,
                                                            PyTango.READ,1000),
                                       self.read_dyn_attr,None,
                                       (lambda s,req_type,attr_name=aname+'_'+suffix: True))
                    if self.UseEvents: 
                        self.set_change_event(aname+'_'+suffix, True, False)
        #self._dyn_attr_build = True
        self.change_state(PyTango.DevState.ON)
        return
  
#------------------------------------------------------------------
#    Device constructor
#------------------------------------------------------------------
    def __init__(self,cl, name):
        PyTango.Device_4Impl.__init__(self,cl,name)
        #self._dyn_attr_build = False
        ProcessProfiler.init_device(self)
        #self.log = fn.Logger('ProcessProfiler/%s'%name)
        #self.info_stream = self.log.info
        #self.warning_stream = self.error_stream = self.log.warning

#------------------------------------------------------------------
#    Device destructor
#------------------------------------------------------------------
    def delete_device(self):
        #self.debug_stream("[Device delete_device method] for device",self.get_name())
        return


#------------------------------------------------------------------
#    Device initialization
#------------------------------------------------------------------
    def init_device(self):
        #self.debug_stream("In ", self.get_name(), "::init_device()")
        self.set_state(PyTango.DevState.INIT)
        self.get_device_properties(self.get_device_class())
        
        if self.UseEvents:
            for a in ['State','Status','LoadAverage','MaxRss','MaxRssProcess',
                      'MemUsage','MemRate','NTasks','UpdateLapseTime']:
                self.set_change_event(a, True, False)
        
        self._important_logs = []
        self._loadAverage = []
        self.values = {}
        self.failed = {}
        self.leaks = {} #For each process time,memory,leak/minute will be recorded every 600s.
        self._nCPUs = 1 #cpu_count()
        self._PID = os.getpid()
        self._memrate = 0.
        self.updateThread = None
        self.lapseTime = None
        self.maxrss, self.maxrsspid, self.maxrssname = 0,0,''
        self._total, self._free, self._cached, self._used = 1,0,0,0
        print 'Ready to receive request ...\n\n'
        self.dyn_attr()#necessary to re-populate dynamic attributes if the property list have changed and device Init().
        

#------------------------------------------------------------------
#    Always excuted hook method
#------------------------------------------------------------------
    @memory_checker
    def always_executed_hook(self):
        try:
            #self.debug_stream("In ", self.get_name(), "::always_excuted_hook()")
            default = 'Device is %s'%self.get_state()
            if self.failed: 
                msg = 'Process not found:]\n%s'%'\n'.join(sorted(str(t) for t in self.failed.items()))
                self.set_status(msg)
                print(self.get_status())
            else:
                status = default
                status += '\nTotal: %s, Used: %s' % (self._total,self._used)
                status += '\nFree: %s, Cached: %s' % (self._free,self._cached)
                status += '\nLoad: %s' % str(self._loadAverage)
                status += '\nMaxRss: PID %s (%s kb)\n%s' % (
                    self.maxrsspid, self.maxrss, self.maxrssname)
                self.set_status(status)
            #elif self.get_status()!=default: 
                #self.set_status(default)
                #print self.get_status()
        except:
            self.set_status(traceback.format_exc())
            self.set_state(PyTango.DevState.UNKNOWN)
            print(self.get_status())

#==================================================================
#
#    ProcessProfiler read/write attribute methods
#
#==================================================================
#------------------------------------------------------------------
#    Read Attribute Hardware
#------------------------------------------------------------------
    def read_attr_hardware(self,data):
        #self.debug_stream("In ", self.get_name(), "::read_attr_hardware()")
        pass

    def read_MaxRss(self, attr):
        #self.debug_stream("In %s::read_MaxRss()"%self.get_name())
        attr.set_value(self.maxrss)
        
    def read_MaxRssProcess(self, attr):
        #self.debug_stream("In %s::read_MaxRssProcess()"%self.get_name())
        attr.set_value(self.maxrssname)
        
#------------------------------------------------------------------
#    Read LoadAverage attribute
#------------------------------------------------------------------
    def read_LoadAverage(self, attr):
        self.debug_stream("In %s::read_LoadAverage()"%self.get_name())
        
        #    Add your own code here
        
        attr.set_value(self._loadAverage, len(self._loadAverage))

#------------------------------------------------------------------
#    Read nCPUs attribute
#------------------------------------------------------------------
    def read_nCPUs(self, attr):
        #self.debug_stream("In %s::nCPUs()"%self.get_name())
        
        #    Add your own code here
        
        attr.set_value(self._nCPUs)
        
    def read_UpdateLapseTime(self, attr):
        #self.debug_stream("In %s::UpdateLapseTime()"%self.get_name())
        
        #    Add your own code here
        
        attr.set_value(self.lapseTime)
        
#------------------------------------------------------------------
#    Read MemUsage attribute
#------------------------------------------------------------------
    def read_MemUsage(self, attr=None):
        #self.debug_stream("In read_MemUsage()")
        
        #    Add your own code here
        if self._PID in self.all_proc:
            v = self.all_proc[self._PID]['rss']
        else:
            v = self.getMemUsage()
        if attr is not None:
            attr.set_value(v)
        return v
        
#------------------------------------------------------------------
#    Read MemRate attribute
#------------------------------------------------------------------        
        
    def read_MemRate(self, attr):
        #self.debug_stream("In read_MemRate()")
        
        #    Add your own code here
        attr.set_value(self._memrate)
        
#------------------------------------------------------------------
#    Read NTasks attribute
#------------------------------------------------------------------        
        
    def read_NTasks(self, attr):
        #self.debug_stream("In read_NTasks()")
        
        #    Add your own code here
        attr.set_value(self._nTasks)

#==================================================================
#
#    ProcessProfiler command methods
#
#==================================================================

#------------------------------------------------------------------
#    Update command:
#
#    Description: This command will trigger the update of the dynamic attributes values for all listed processes.
#                
#------------------------------------------------------------------
    @memory_checker
    def Update(self):
        #self.info_stream
        tracer("In %s::Update(%s)"%(self.get_name(),self.Threaded))
        #    Add your own code here
        try:
            if self.get_state() == PyTango.DevState.INIT:
                #self.warn_stream("Not yet initialized to start an update.")
                return
            self._loadAverage = list(os.getloadavg())
            try:
                self._nTasks = int(shell_command("ps auxwwH|wc -l"))
            except:
                traceback.print_exc()
                self._nTasks = 0
                
            #do in a separate thread to avoid to hang the device if it takes too long
            if self.Threaded:
                if not self.updateThread == None and self.updateThread.is_alive():
                    #self.warn_stream("Try to update when not finish yet last call")
                    self.change_state(PyTango.DevState.ALARM)
                    self.addStatusMsg("Update() command call overlapped with a non finish previous call")
                else:
                    if self.updateThread is not None: del self.updateThread
                    #self.updateThread = Process(target=self.update_ProcessList)
                    self.updateThread = threading.Thread(target=self.update_ProcessList)
                    self.updateThread.run()
                    self.change_state(PyTango.DevState.ON)
                    self.addStatusMsg("")
            else:
                self.update_ProcessList()
                self.change_state(PyTango.DevState.ON)
        except Exception,e:
            self.error_stream("Update() exception: %s"%(str(e)))
            
        
    def update_ProcessList(self):
        try:
            self.debug_stream('update_ProcessList(%s)' % self.UseEvents)
            startTime = time.time()
            #self._loadAverage = [] #list(os.getloadavg())
            #self._update_without_thread_split()#self._update_without_thread_split()
            self.update_all_processes()
            self.getMemRate()
            self.lapseTime = time.time()-startTime
            #self.info_stream('Update() finished in %6.3f seconds'%(self.lapseTime))
            if self.UseEvents: 
                events = [('MemUsage',self.read_MemUsage()),
                          ('LoadAverage',self._loadAverage),
                          ('NTasks',self._nTasks),
                          ('MemRate',self._memrate),
                          ('MaxRss',self.maxrss),
                          ('MaxRssProcess',self.maxrssname),
                          ['UpdateLapseTime',self.lapseTime],
                          ]                
                self.fireEventsList(events)
            return
        except:
            self.error_stream('Unable to launch process list update:\n%s'%(traceback.format_exc()))
    
    #def _update_with_thread_split(self):#FIXME: Not used, needs further work
        #subthreadsList = []
        #for process in self.ProcessList:
            #subthread = threading.Thread(target=self.update_process,args=[process])
            #subthread.run()
            #subthreadsList.append(subthread)
        #while subthreadsList != []:
            #for i,subthread in enumerate(subthreadsList):
                #if not subthread.isAlive():
                    #subthreadsList.pop(i)
                    
    def _update_without_thread_split(self):
        for process in self.ProcessList:
            self.update_process(process)
            
    def update_all_processes(self):
        #tracer('update_all_processes()')
        self.all_proc = get_all_process()
        p = get_worse_process(self.all_proc,'rss')
        self.maxrss = self.all_proc[p]['rss']
        self.maxrsspid = p
        self.maxrssname = self.all_proc[p]['cmd']
        for process in self.ProcessList:
            self.update_process(process)

    def update_process(self,process):
        #self.info_stream
        #tracer('update_process(%s)'%process)
        aname = re.sub('[^0-9a-zA-Z]+','_',process)
        processes = []
        nthreads,cpu,mem,vmem,memRatio = None,None,None,None,None
        try:
            processes = [k for k,v in self.all_proc.items() 
                if not v['cmd'].lower().startswith('screen ') and re.search(process,v['cmd'])] #get_processes_pid(process)
            #self.debug_stream('\t#processes: %d'%len(processes))
            nthreads = 0
            cpu = 0
            mem = 0
            vmem = 0
            memRatio = 0
            if not processes == []:
                for each_process in processes:
                    subthreads,subcpu,submemRatio,submem,subvmem = [self.all_proc[each_process][k] for k in ('threads','cpu','mem','rss','vsize')]#self.update_subprocess(each_process)
                    nthreads += subthreads
                    cpu += subcpu
                    mem += submem
                    vmem += subvmem
                    memRatio += submemRatio
                #self.debug_stream('\ttotal #threads: %d'%nthreads)
                #self.debug_stream('\ttotal cpu: %f'%cpu)
                #self.debug_stream('\ttotal mem: %f'%mem)
                #self.debug_stream('\ttotal vmem: %f'%vmem)
                #self.debug_stream('\ttotal mem ratio: %f'%memRatio)
            self.values[aname+'_nprocesses']=len(processes)
            self.values[aname+'_nthreads']=nthreads
            self.values[aname+'_pids']=processes
            self.values[aname+'_cpu']=cpu
            self.values[aname+'_mem']=mem
            self.values[aname+'_vmem']=vmem
            self.values[aname+'_memRatio']=memRatio
            
            if aname not in self.leaks:
                self.leaks[aname] = (time.time(),float(mem),0)
            elif (self.leaks[aname][0]+600)<time.time():
                self.leaks[aname] = (time.time(),mem,60*1e3*(mem-self.leaks[aname][1])/(time.time()-self.leaks[aname][0]))
            self.values[aname+'_kbpm'] = self.leaks[aname][-1]
            
            if self.UseEvents:
                events = []
                for suffix in ['nprocesses','nthreads','pids','cpu','mem','vmem','memRatio','kbpm']:
                    events.append([aname+'_'+suffix,self.values[aname+'_'+suffix]])
                self.fireEventsList(events)
        except Exception,e:
            self.failed.pop(aname,None)
            self.error_stream('Unable to get values for process %s:\n%s'%(process,traceback.format_exc()))
            self.failed[aname] = process
        return

    #def update_subprocess(self,subprocess):
        #self.debug_stream('\tprocess: %d'%subprocess)
##        subprocess_threads = get_nthreads(subprocess)
##        self.debug_stream('\t\t#threads: %d'%subprocess_threads)
##        subprocess_cpu = get_cpu(subprocess)
##        self.debug_stream('\t\tcpu: %f'%subprocess_cpu)
##        subprocess_mem = get_memory(subprocess)
##        self.debug_stream('\t\tmem: %f'%subprocess_mem)
        #subprocess_threads,subprocess_cpu,subprocess_memRatio,subprocess_mem,subprocess_vmem = get_threads_cpu_and_memory(subprocess)
        #self.debug_stream('\t\t#threads: %d'%subprocess_threads)
        #self.debug_stream('\t\tcpu: %f'%subprocess_cpu)
        #self.debug_stream('\t\tmem: %f'%subprocess_mem)
        #self.debug_stream('\t\tvmem: %f'%subprocess_vmem)
        #self.debug_stream('\t\tmem ratio: %f'%subprocess_memRatio)
        #return [subprocess_threads,
                #subprocess_cpu,
                #subprocess_memRatio,
                #subprocess_mem,
                #subprocess_vmem]
                
#------------------------------------------------------------------
#    evaluateFormula command:
#------------------------------------------------------------------                

    def evaluateFormula(self,argin):
        t0 = time.time()
        tracer('\tevaluateFormula(%s)'%(argin,))
        try:
            argout = eval(str(argin),globals(),locals())
        except Exception,e:
            argout = e
        tracer('\tevaluateFormula took %s seconds'%(time.time()-t0))
        return str(argout)

#==================================================================
#
#    ProcessProfilerClass class definition
#
#==================================================================
class ProcessProfilerClass(PyTango.PyDeviceClass):

    #    Class Properties
    class_property_list = {
        }


    #    Device Properties
    device_property_list = {
        'ProcessList':
            [PyTango.DevVarStringArray,
            "List of processes to be monitorized",
            [] ],
        'UseEvents':
            [PyTango.DevBoolean,
            "Whether to push events or not",
            [ False ] ],
        'Threaded':
            [PyTango.DevBoolean,
            "Whether to use threads or not",
            [ False ] ],
        }


    #    Command definitions
    cmd_list = {
        'Update':
            [[PyTango.DevVoid, ""],
            [PyTango.DevVoid, ""],
            {
                'Polling period': 10000,
            } ],
        'evaluateFormula':
            [[PyTango.DevString, "formula to evaluate"],
            [PyTango.DevString, "formula to evaluate"],
            {
                'Display level':PyTango.DispLevel.EXPERT,
             } ],            
        }


    #    Attribute definitions
    attr_list = {
        'MaxRss':
            [[PyTango.DevDouble,
            PyTango.SCALAR,
            PyTango.READ],
            {
                'unit':'kb',
            } ],            
        'MaxRssProcess':
            [[PyTango.DevString,
            PyTango.SCALAR,
            PyTango.READ],
            ],
        'LoadAverage':
            [[PyTango.DevDouble,
            PyTango.SPECTRUM,
            PyTango.READ, 3],
            {
                'label':"LoadAverage",
                'description':"one, five, and fifteen minute averages",
            } ],
        'nCPUs':
            [[PyTango.DevShort,
            PyTango.SCALAR,
            PyTango.READ],
            {
                'label':'CPUs',
                'description':'Number of CPUs in this machine',
            } ],
        'UpdateLapseTime':
            [[PyTango.DevDouble,
            PyTango.SCALAR,
            PyTango.READ],
            {
                'label':'Update lapsetime',
                'description':'Time used by the Update() command to proceed',
                'unit':'s',
            } ],
       'MemUsage':
           [[PyTango.DevDouble,
           PyTango.SCALAR,
           PyTango.READ],
            {
                'description': 'This attribute returns the memory of OWN process',
                'unit':'kb',
            } ],
       'MemRate':
           [[PyTango.DevDouble,
           PyTango.SCALAR,
           PyTango.READ],
            {
                'description': 'This attribute returns total-(free+cached) memory',
                'unit':' ',
            } ],            
       'NTasks':
           [[PyTango.DevLong,
           PyTango.SCALAR,
           PyTango.READ],
            {
                'description': 'Number of Tasks/Threads on this host',
                'unit':' ',
            } ],                        
        }

    #Needed to have proper dynamic attributes
    def dyn_attr(self,dev_list):
        for dev in dev_list:
            try: dev.dyn_attr()
            except: print traceback.format_exc()

#------------------------------------------------------------------
#    ProcessProfilerClass Constructor
#------------------------------------------------------------------
    def __init__(self, name):
        PyTango.PyDeviceClass.__init__(self, name)
        self.set_type(name);
        print "In ProcessProfilerClass  constructor"

#==================================================================
#
#    ProcessProfiler class main method
#
#==================================================================
if __name__ == '__main__':
    try:
        py = PyTango.Util(sys.argv)
        py.add_TgClass(ProcessProfilerClass,ProcessProfiler,'ProcessProfiler')

        U = PyTango.Util.instance()
        U.server_init()
        U.server_run()

    except PyTango.DevFailed,e:
        print '-------> Received a DevFailed exception:',e
    except Exception,e:
        print '-------> An unforeseen exception occured....',e
