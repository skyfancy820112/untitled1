# -*- coding: utf-8 -*-
import hashlib,urllib,math,winreg,pyperclip,collections
import sys,configparser,os,time,csv,datetime,shutil
import requests,json,threading
from requests.adapters import HTTPAdapter
from PyQt5.QtCore import QDate, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QProgressBar, QFileDialog
from mainForm import *
from PIL import Image
from io import BytesIO
from numpy import average, dot, linalg

class MyMainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self, parent=None):
		super(MyMainWindow, self).__init__(parent)
		self.setupUi(self)
		self.setWindowTitle("小程序工具集")
		#向状态栏添加一个progressbar
		self.info_lable=QLabel()
		self.info_progressbar=QProgressBar()
		self.statusBar().addPermanentWidget(self.info_lable)
		self.statusBar().addPermanentWidget(self.info_progressbar)
		self.info_progressbar.setGeometry(0,0,100,5)
		self.info_progressbar.setRange(0,500)
		self.info_progressbar.setValue(0)
		#初始化事件控件默认自
		self.sel_begindate.setDate(QDate.currentDate())
		self.sel_enddate.setDate(QDate.currentDate())
		self.sel_begindate.setMaximumDate(QDate.currentDate())
		self.sel_enddate.setMaximumDate(QDate.currentDate())
		self.sel_begindate.setDisplayFormat("yyyy-MM-dd")
		self.sel_enddate.setDisplayFormat("yyyy-MM-dd")
		self.sel_store_vaild_status.setCurrentIndex(1)
		self.sel_store_balance_status.setCurrentIndex(1)
		#初始化radio
		self.rb_hx_type_max.setChecked(True)
		#登陆前默认按钮不可用
		self.btn_hy_imp.setEnabled(False)
		self.btn_hd_imp.setEnabled(False)
		self.btn_hd_find.setEnabled(False)
		self.btn_hx_find.setEnabled(False)
		self.btn_paydetail_imp.setEnabled(False)
		self.btn_store_imp.setEnabled(False)
		self.btn_image_add.setEnabled(False)
		self.btn_image_del.setEnabled(False)
		self.btn_image_resume.setEnabled(False)
		#加载配置文件
		set_dict=wmEvent_loadCfg()
		#print(set_dict)
		if set_dict:
			self.tx_username.setText(set_dict["username"])
			self.tx_password.setText(set_dict["password"])
			self.tx_hy_code.setText(set_dict["quancode"])
			self.tx_hd_code.setText(set_dict["hdcode"])
			self.tx_hx_grp1_name.setText(set_dict["grp1name"])
			self.tx_hx_grp1_max.setText(set_dict["grp1max"])
			self.tx_hx_grp1_codelist.setText(set_dict["grp1list"])
			self.tx_hx_grp2_name.setText(set_dict["grp2name"])
			self.tx_hx_grp2_max.setText(set_dict["grp2max"])
			self.tx_hx_grp2_codelist.setText(set_dict["grp2list"])
			self.chb_proxy.setChecked(set_dict["useproxy"])
			self.tx_proxy_name.setText(set_dict["proxyusername"])
			self.tx_proxy_password.setText(set_dict["proxypassword"])
			if set_dict["useproxy"]==False:
				self.tx_proxy_name.setEnabled(False)
				self.tx_proxy_password.setEnabled(False)
		#界面响应事件绑定
		self.sel_enddate.dateChanged.connect(lambda:wmEvent_datechange(self))
		self.btn_login.clicked.connect(lambda:wmEvent_login(self))
		self.chb_proxy.stateChanged.connect(lambda:wmEvent_checkchange(self))
		self.btn_hy_imp.clicked.connect(lambda:get_Hylist(self))
		#self.btn_hd_imp.clicked.connect(lambda:get_Hdlist(self))
		self.btn_hd_imp.clicked.connect(lambda: wmEvent_info(self,1))
		self.btn_hd_find.clicked.connect(lambda:wmEvent_info(self,0))
		self.btn_store_imp.clicked.connect(lambda:get_store_list(self))
		self.btn_hx_find.clicked.connect(lambda:get_group_data(self))
		self.btn_paydetail_imp.clicked.connect(lambda:get_paydetail_list(self))
		self.btn_image_resume.clicked.connect(lambda:wmEvent_image_resume(self))
		self.btn_image_del.clicked.connect(lambda:wmEvent_image_del(self))
		self.btn_image_add.clicked.connect(lambda:wmEvent_image_add(self))

	def closeEvent(self,event):
		reply = QtWidgets.QMessageBox.question(self,"确认操作","是否要退出程序？",
											   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
											   QtWidgets.QMessageBox.No)
		if reply == QtWidgets.QMessageBox.Yes:
			wmEvent_writeCfg(self)
			event.accept()
		else:
			event.ignore()

#全局函数定义
G_login=False #登陆状态
G_Session = requests.session() #全局http_session
G_cookies=requests.cookies.RequestsCookieJar() #http_requests的cookie参数
G_Url=""#通用URL传递参数
G_Refer=""#通用referer传递参数
G_List = {} #存储登陆返回信息的字典
G_List["areacode"]="10015"
G_List["centercode"]="1001"
G_List["groupcode"]="101"
G_List["dnt"]="1"
G_maxpage=0
G_maxrecord=0
#==========================================================================================================
#
#以下代码为窗体响应类实现代码
#
#==========================================================================================================

def wmEvent_info(self,type):
	if type==0:
		QtWidgets.QMessageBox.about(self, "小小的遗憾", "此功能尚在开发阶段")
	else:
		QtWidgets.QMessageBox.about(self, "一个很不愉快的消息", "小程序中台暂时关闭了此功能")

#响应结束时间选择事件：起始时间应当小于结束时间且其实时间最大值应根据结束时间当前值进行调整
def wmEvent_datechange(self):
	bdate=self.sel_begindate.date()
	edate=self.sel_enddate.date()
	if edate<bdate:
		self.sel_begindate.setDate(edate)
		self.sel_begindate.setMaximumDate(edate)

#响应代理启用按钮的事件
def wmEvent_checkchange(self):
	if self.chb_proxy.isChecked():
		self.tx_proxy_name.setEnabled(True)
		self.tx_proxy_password.setEnabled(True)
	else:
		self.tx_proxy_name.setEnabled(False)
		self.tx_proxy_password.setEnabled(False)

#响应加载配置文件
def wmEvent_loadCfg():
	file_ex = os.path.exists("set.cfg")
	set_dict={}
	if file_ex == True:
		try:
			config = configparser.RawConfigParser()
			config.read("set.cfg")
			if config.has_section("userinfo"):
				if config.has_option("userinfo","username"):
					set_dict["username"] = config.get("userinfo", "username")
				else:
					set_dict["username"]=""
				if config.has_option("userinfo","password"):
					set_dict["password"] = config.get("userinfo", "password")
				else:
					set_dict["password"]=""
			else:
				set_dict["username"] = ""
				set_dict["password"] = ""
			if config.has_section("appset"):
				if config.has_option("appset", "quancode"):
					set_dict["quancode"] = config.get("appset", "quancode")
				else:
					set_dict["quancode"]=""
				if config.has_option("appset", "hdcode"):
					set_dict["hdcode"] = config.get("appset", "hdcode")
				else:
					set_dict["hdcode"]=""
				if config.has_option("appset", "grp1name"):
					set_dict["grp1name"] = config.get("appset", "grp1name")
				else:
					set_dict["grp1name"]=""
				if config.has_option("appset", "grp2name"):
					set_dict["grp2name"] = config.get("appset", "grp2name")
				else:
					set_dict["grp2name"]=""
				if config.has_option("appset", "grp1max"):
					set_dict["grp1max"] = config.get("appset", "grp1max")
				else:
					set_dict["grp1max"]=""
				if config.has_option("appset", "grp2max"):
					set_dict["grp2max"] = config.get("appset", "grp2max")
				else:
					set_dict["grp2max"]=""
				if config.has_option("appset", "grp1list"):
					set_dict["grp1list"] = config.get("appset", "grp1list")
				else:
					set_dict["grp1list"]=""
				if config.has_option("appset", "grp2list"):
					set_dict["grp2list"] = config.get("appset", "grp2list")
				else:
					set_dict["grp2list"]=""
			else:
				set_dict["quancode"] = ""
				set_dict["hdcode"] = ""
				set_dict["grp1name"] = ""
				set_dict["grp2name"] = ""
				set_dict["grp1max"] = ""
				set_dict["grp2max"] = ""
				set_dict["grp1list"] = ""
				set_dict["grp2list"] = ""
			if config.has_section("proxy"):
				if config.has_option("proxy","useproxy"):
					set_dict["useproxy"]=config.getboolean("proxy","useproxy")
				else:
					set_dict["useproxy"]=False
				if config.has_option("proxy","proxyusername"):
					set_dict["proxyusername"]=config.get("proxy","proxyusername")
				else:
					set_dict["proxyusername"]=""
				if config.has_option("proxy","proxypassword"):
					set_dict["proxypassword"]=config.get("proxy","proxypassword")
				else:
					set_dict["proxypassword"]=""
			else:
				set_dict["useproxy"] = False
				set_dict["proxyusername"] = ""
				set_dict["proxypassword"] = "a"
		except:
			set_dict = {}
	return set_dict

#响应关闭写入配置文件
def wmEvent_writeCfg(self):
	set_dict={}
	set_dict["username"] = self.tx_username.text()
	set_dict["password"] = self.tx_password.text()
	set_dict["quancode"] = self.tx_hy_code.text()
	set_dict["hdcode"] = self.tx_hd_code.text()
	set_dict["grp1name"] = self.tx_hx_grp1_name.text()
	set_dict["grp2name"] = self.tx_hx_grp2_name.text()
	set_dict["grp1max"] = self.tx_hx_grp1_max.text()
	set_dict["grp2max"] = self.tx_hx_grp2_max.text()
	set_dict["grp1list"] = self.tx_hx_grp1_codelist.text()
	set_dict["grp2list"] = self.tx_hx_grp2_codelist.text()
	set_dict["useproxy"]=self.chb_proxy.isChecked()
	set_dict["proxyusername"]=self.tx_proxy_name.text()
	set_dict["proxypassword"]=self.tx_proxy_password.text()
	#print(set_dict)
	config = configparser.RawConfigParser()
	config.add_section("userinfo")
	config.set("userinfo", "username", set_dict["username"])
	config.set("userinfo", "password", set_dict["password"])
	config.add_section("appset")
	config.set("appset","quancode",set_dict["quancode"])
	config.set("appset","hdcode",set_dict["hdcode"])
	config.set("appset","grp1name",set_dict["grp1name"])
	config.set("appset","grp2name",set_dict["grp2name"])
	config.set("appset","grp1max",set_dict["grp1max"])
	config.set("appset","grp2max",set_dict["grp2max"])
	config.set("appset","grp1list",set_dict["grp1list"])
	config.set("appset","grp2list",set_dict["grp2list"])
	config.add_section("proxy")
	config.set("proxy","useproxy",set_dict["useproxy"])
	config.set("proxy","proxyusername",set_dict["proxyusername"])
	config.set("proxy","proxypassword",set_dict["proxypassword"])
	with open('set.cfg', 'w') as configfile:
		config.write(configfile)

def wmEvent_login(self):
	username = self.tx_username.text()
	password = self.tx_password.text()
	md5_password=hashlib.md5(password.encode(encoding='UTF-8')).hexdigest()
	G_Url="https://center.beyonds.com/permission/voyager/basisb/v1/user/login"
	G_Refer="https://center.beyonds.com/web/"
	G_Json={"userName": username, "password": md5_password, "channel": 0, "type": 0}
	jsondata=json.dumps(G_Json)
	try:
		rs = webPost(G_Url, G_Refer, jsondata)
		if int(rs.status_code == 200):
			G_login = True
		else:
			G_login = False
	except:
		G_login = False
	if G_login:
		self.btn_store_imp.setEnabled(True)
		self.btn_hx_find.setEnabled(True)
		self.btn_hy_imp.setEnabled(True)
		self.btn_hd_find.setEnabled(True)
		self.btn_hd_imp.setEnabled(True)
		self.btn_paydetail_imp.setEnabled(True)
		self.btn_image_add.setEnabled(True)
		self.btn_image_del.setEnabled(True)
		self.btn_image_resume.setEnabled(True)
		self.statusBar().showMessage("登陆成功")
	else:
		self.statusBar().showMessage("登陆失败")
	return G_login

#==============================================================================================
#
#以下为通用方法实现
#
#==============================================================================================

#获取当前设备的桌面的方法
def get_desktop():
	key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
	return winreg.QueryValueEx(key, "Desktop")[0]
#判断文件是否是图片类型
def isValidImage(pathfile):
	(file_path,file_name)=os.path.split(pathfile[0])
	(file_sname,file_type)=os.path.splitext(file_name)
	newfile="temp"+file_type
	old_abs_file=os.path.join(file_path,file_name).replace("\\","/")
	new_abs_file=os.path.abspath(newfile).replace("\\","/")
	#print(old_abs_file,new_abs_file)
	shutil.copyfile(old_abs_file,new_abs_file)
	bVilad_dict={}
	bValid = True
	try:
		Image.open(newfile).verify()
		bVilad_dict["isimage"]=True
		bVilad_dict["filename"]=newfile
	except:
		bVilad_dict["isimage"]=True
		bVilad_dict["filename"]=newfile
	return bVilad_dict
#从URL地址获取图片信息
def getImageByUrl(url,http_proxy):
	# 根据图片url 获取图片对象
	bl_used = False
	try:
		bl_used = http_proxy["isused"]
		bl_proxy_username = http_proxy["username"]
		bl_proxy_password = http_proxy["password"]
	except :
		bl_used = False
	if bl_used == False:
		html = requests.get(url, verify=False)
	else:
		proxy_dict={}
		proxy_dict["http"]="http://"+bl_proxy_username+":"+bl_proxy_password+"@proxy.wanda.cn:8080/"
		proxy_dict["https"]="https://"+bl_proxy_username+":"+bl_proxy_password+"@proxy.wanda.cn:8080/"
		#print(proxy_dict)
		html = requests.get(url, proxies = proxy_dict, verify=False)
	image = Image.open(BytesIO(html.content))
	return image

# 对图片进行统一化处理
def get_thum(image, size=(64,64), greyscale=False):
	# 利用image对图像大小重新设置, Image.ANTIALIAS为高质量的
	image = image.resize(size, Image.ANTIALIAS)
	if greyscale:
		# 将图片转换为L模式，其为灰度图，其每个像素用8个bit表示
		image = image.convert('L')
	return image

# 计算图片的余弦距离
def image_sim(image1, image2):
	image1 = get_thum(image1)
	image2 = get_thum(image2)
	images = [image1, image2]
	vectors = []
	norms = []
	for image in images:
		vector = []
		for pixel_tuple in image.getdata():
			vector.append(average(pixel_tuple))
		vectors.append(vector)
		# linalg=linear（线性）+algebra（代数），norm则表示范数
		# 求图片的范数？？
		norms.append(linalg.norm(vector, 2))
	a, b = vectors
	a_norm, b_norm = norms
	# dot返回的是点积，对二维数组（矩阵）进行计算
	res = dot(a / a_norm, b / b_norm)
	#print("图片相似度：",res)
	return res

#加载通用方法，用于登陆并且返回用户信息
def webPost(purl,prefer,pdata):
	requests.packages.urllib3.disable_warnings()
	ps = G_Session
	postheaders = {}
	postheaders["content-type"]="application/json;charset=UTF-8"
	postheaders["referer"]=prefer
	postheaders["user-agent"]="Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
	postheaders["dnt"]=G_List["dnt"]
	postheaders["accept"]="application/json, text/plain, */*"
	sText = ps.post(purl,headers=postheaders,data=pdata,verify=False)
	rs = json.loads(sText.text)
	G_List["token"]=rs["data"]["token"]
	G_List["placeid"]=rs["data"]["orgList"][0]["id"]
	G_List["tenantId"]=str(rs["data"]["tenantId"])
	G_List["orgId"]=rs["data"]["orgId"]
	G_List["orgCode"]=rs["data"]["orgCode"]
	G_List["orgName"]=rs["data"]["orgName"]
	G_List["id"]=rs["data"]["id"]
	G_List["code"]=rs["data"]["code"]
	G_List["name"]=rs["data"]["name"]
	G_List["orgTypeCode"]=rs["data"]["orgList"][0]["orgTypeCode"]
	G_List["orgTypeName"]=rs["data"]["orgList"][0]["orgTypeName"]
	mycookies = sText.request._cookies
	G_cookies = requests.utils.dict_from_cookiejar(mycookies)
	return sText

#获取图片的字节信息
def ToLoadbytes(filename):
	with open(filename,"rb") as f:#转为二进制格式
		base64_data = f.read()
		f.close()
	return base64_data


#向图云提交图片资源，并返回图片在图云上的URL
def PostImage(purl,ref,filename):
	requests.packages.urllib3.disable_warnings()
	ps = requests.session();
	postheaders = {}
	boundaryname = str(int(time.time()*1000))
	#postheaders["Content-Type"]="multipart/form-data; boundary=----"+boundaryname
	postheaders["code"]=G_List["orgCode"]
	postheaders["orgcode"]=G_List["orgCode"]
	postheaders["orgName"]=urllib.parse.quote(G_List["orgName"])
	postheaders["orgTypeCode"]=G_List["orgTypeCode"]
	postheaders["Referer"]=ref
	postheaders["tenantId"]=G_List["tenantId"]
	postheaders["token"]=G_List["token"]
	postheaders["userid"]=G_List["id"]
	postheaders["username"]=urllib.parse.quote(G_List["name"])
	postheaders["workingOrgCode"] = G_List["orgCode"]
	#print(postheaders)
	Imagebyte = ToLoadbytes(filename)
	file_name= os.path.basename(filename)
	f={"file":(file_name,open(filename,"rb"),"image/jpeg")}
	ps.cookies = G_cookies
	ps.headers = postheaders
	rs = ps.post(purl,files=f,verify=False)
	rslist = json.loads(rs.text)
	return rslist

#发送数据报文通用方法，包含get和post两种方法的头文件都在里面，store_list特指门头维护
def webRequest(v_method,purl,ref,pdata,type_head):
	requests.packages.urllib3.disable_warnings()
	gs=G_Session
	gs.mount('https://', HTTPAdapter(max_retries=3))
	getheaders={}
	getheaders["content-type"] = "application/json;charset=UTF-8"
	getheaders["accept"] = "application/json,text/plain,*/*"
	getheaders["token"] = G_List["token"]
	getheaders["groupcode"] = G_List["groupcode"]
	getheaders["areacode"] = G_List["areacode"]
	getheaders["centercode"] = G_List["centercode"]
	getheaders["plazacode"] = G_List["orgCode"]
	getheaders["storecode"] = ""
	getheaders["orgcode"] = G_List["orgCode"]
	getheaders["workingorgcode"] = G_List["orgCode"]
	getheaders["orgname"] = urllib.parse.quote(G_List["orgName"].strip())
	getheaders["tenantid"] = G_List["tenantId"]
	getheaders["orgtypecode"] = G_List["orgTypeCode"]
	getheaders["orgtypename"] = urllib.parse.quote(G_List["orgTypeName"].strip())
	getheaders["userid"] = G_List["id"]
	getheaders["username"] = urllib.parse.quote(G_List["name"].strip())
	getheaders["connection"] = "keep-alive"
	getheaders["host"] = "center.beyonds.com"
	getheaders["referer"] = ref
	getheaders["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
	if type_head=="store_list":
		pdata = pdata.replace(" ","")
		getheaders["content-length"]=str(len(pdata.replace(" ","")))
	elif type_head=="hd_list":
		#getheaders["dnt"]=G_List["dnt"].strip()
		pass
	elif type_head=="detail_list":
		getheaders["dnt"] = G_List["dnt"].strip()
	else:
		pass
	#print(getheaders)
	gs.headers = getheaders
	gs.cookie = G_cookies
	try_count=0
	while try_count<=3:
		try:
			if v_method=="get":
				sText = gs.get(purl,params=pdata, verify=False,timeout=5)
			if v_method=="post":
				sText = gs.post(purl,data=pdata,verify=False,timeout=5)
			if int(sText.status_code)==200:
				break
		except requests.exceptions.RequestException as e:
			print(e)
		try_count+=1
	#print(sText.url)
	return sText

#================================================================================================
#
#以下为业务逻辑实现函数与类
#
#=================================================================================================


#获取大转盘，抽奖等活动信息
def get_Hdlist(self):
	G_maxrecord=0
	G_maxpage=0
	hdcode=self.tx_hd_code.text()
	p_status_index=self.sel_hd_status.currentIndex()
	status_dict={"0":"1","1":None}
	p_status =status_dict[str(p_status_index)]
	bdate = self.sel_begindate.date().toString("yyyy-M-dd")
	edate = self.sel_enddate.date().toString("yyyy-M-dd")
	G_Url="https://center.beyonds.com/fortune/fortune/history"
	G_Refer="https://center.beyonds.com/web-parking/"
	params_dict={}
	params_dict["drawStartTime"]=bdate
	params_dict["drawEndTime"]=edate
	params_dict["sendStatus"]=p_status
	params_dict["pageIndex"]="1"
	params_dict["pageSize"]="100"
	ps=G_Session
	hdcode_list=hdcode.split(",")
	code_dict={}
	for per_hdcode in hdcode_list:
		params_dict["activityId"]=per_hdcode
		params_dict["timestr"]=str(int(time.time()*1000))
		rs=webRequest("get",G_Url,G_Refer,params_dict,"hd_list")
		rs_json=json.loads(rs.text)
		if int(rs.status_code)==200:
			per_maxrecode=int(rs_json["totalCount"])
			G_maxrecord+=per_maxrecode
			#print(per_maxrecode,G_maxrecord)
			per_maxpage=int(rs_json["totalPage"])
			G_maxpage+=per_maxpage
			#print(per_maxpage,G_maxpage)
			code_dict[per_hdcode]=per_maxpage
			self.statusBar().showMessage("正在查询，请稍后")
			QApplication.processEvents()
	self.info_progressbar.setRange(0,G_maxrecord)
	self.info_lable.setText("共" + str(G_maxrecord) + "条数据，共" + str(G_maxpage) + "页")
	QApplication.processEvents()
	csv_title=["memberId","mobile","prizeName","isPrized","fortuneTime","isSendStatus","awardName","actId","actName"]
	csv_path=get_desktop()
	csv_name=self.tx_hd_code.text+".csv"
	csv_filename=os.path.join(csv_path,csv_name)
	csv_sec_name=self.tx_hd_code.text+str(int(time.time()))+".csv"
	csv_sec_filename=os.path.join(csv_path,csv_sec_name)
	csv_data=[]
	csv_row=0
	for per_hdcode in hdcode_list:
		params_dict["pageIndex"]="1"
		params_dict["activityId"]=per_hdcode
		params_dict["pageSize"]="100"
		params_dict["timestr"]=str(int(time.time()*1000))
		rs=webRequest("get",G_Url,G_Refer,params_dict,"hd_list")
		rs_json=json.loads(rs.text)
		per_maxpage=rs_json["totalPage"]
		for ipage in range(per_maxpage):
			params_dict["pageIndex"]=str(ipage+1)
			rs=webRequest("get",G_Url,G_Refer,params_dict,"hd_list")
			rs_json=json.loads(rs.text)
			for rs_json_data in rs_json["data"]:
				rs_json_data_dict={}
				rs_json_data_dict["memberId"]=rs_json_data["memberId"]+"\t"
				rs_json_data_dict["mobile"]=rs_json_data["mobile"]+"\t"
				rs_json_data_dict["prizeName"]=rs_json_data["prizeName"]
				rs_json_data_dict["isPrized"]=rs_json_data["isPrized"]
				rs_json_data_dict["fortuneTime"]=rs_json_data["fortuneTime"]
				rs_json_data_dict["isSendStatus"]=rs_json_data["isSendStatus"]
				rs_json_data_dict["awardName"]=rs_json_data["awardName"]
				rs_json_data_dict["actId"]=rs_json_data["actId"]
				rs_json_data_dict["actName"]=rs_json_data["actName"]
				csv_row=csv_row+1
				self.info_progressbar.setValue(csv_row)
				QApplication.processEvents()
				if rs_json_data_dict not in csv_data:
					csv_data.append(rs_json_data_dict)
	try:
		with open(csv_filename, "w", newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_name)
	except:
		with open(csv_sec_filename, "w", newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_sec_name)


#获取会员信息并导出到csv文件
def get_Hylist(self):
	G_maxrecord=0
	G_maxpage=0
	quancode = self.tx_hy_code.text()
	p_status_index = self.sel_hy_status.currentIndex()
	status_dict = {"0": "0", "1": "1", "2": "2", "3": "-1", "4": None}
	status_name_dict={"0":"未使用","1":"已使用","2":"已过期","-1":"已作废"}
	p_status = status_dict[str(p_status_index)]
	bdate = str(self.sel_begindate.date().toString("yyyy-MM-dd") + " 00:00:00")
	edate = str(self.sel_enddate.date().toString("yyyy-MM-dd") + " 23:59:59")
	#print(quancode,p_status,bdate,edate)
	G_Url="https://center.beyonds.com/coupon/inner/user/coupons/codes"
	G_Refer="https://center.beyonds.com/web/"
	quancode_list=quancode.split(",")
	params_dict={}
	params_dict["pageIndex"]="1"
	params_dict["pageSize"]="100"
	params_dict["status"] = p_status
	params_dict["getStartTime"]=bdate
	params_dict["getEndTime"]=edate
	params_dict["plazaId"]=G_List["orgCode"]
	params_dict["timestr"]=str(int(time.time()*1000))
	code_dict={}
	for no_code in quancode_list:
		params_dict["no"]=no_code
		rs=webRequest("get",G_Url,G_Refer,params_dict,"")
		#print(rs.text)
		rs_json=json.loads(rs.text)
		if int(rs.status_code)==200:
			per_record=int(rs_json["data"]["totalSize"])
			G_maxrecord=G_maxrecord+per_record
			G_maxpage=G_maxpage+math.ceil(per_record/100)
			code_dict[no_code]=math.ceil(per_record / 100)
			#print(G_maxpage)
			self.statusBar().showMessage("正在查询，请稍后")
			QApplication.processEvents()
	self.info_progressbar.setRange(0,G_maxpage)
	self.info_lable.setText("共" + str(G_maxrecord) + "条数据，共" + str(G_maxpage) + "页")
	QApplication.processEvents()
	csv_title = ["title","getChannelName" ,"mobile","status", "getTime", "useStartTime", "useEndTime"]
	csv_path = get_desktop()
	csv_name = quancode + ".csv"
	csv_sec_name=quancode+str(int(time.time()))+".csv"
	csv_filename = os.path.join(csv_path, csv_name)
	csv_sec_filename=os.path.join(csv_path,csv_sec_name)
	csv_data = []
	csv_data.append({"title":"优惠券名称","getChannelName":"发券渠道","mobile":"领取手机号","status":"券码状态",
					 "getTime":"中奖时间","useStartTime":"优惠券起始时间","useEndTime":"优惠券失效时间"})
	csv_page = 0
	for no_code in quancode_list:
		params_dict["no"] = no_code
		params_dict["pageSize"] = "100"
		per_maxpage=code_dict[no_code]
		for ipage in range(per_maxpage):
			self.statusBar().showMessage("正在处理数据，请稍等")
			QApplication.processEvents()
			params_dict["pageIndex"]=str(ipage+1)
			#print(ipage+1)
			csv_page=csv_page+1
			self.info_progressbar.setValue(csv_page)
			QApplication.processEvents()
			params_dict["timestr"] = str(int(time.time() * 1000))
			rs=webRequest("get",G_Url,G_Refer,params_dict,"")
			#print(rs.text)
			rs_json=json.loads(rs.text)
			#print(rs_json["data"]["list"])
			if rs_json["data"]["list"]:
				row=0
				for rs_json_data in rs_json["data"]["list"]:
					row=row+1
					rs_json_data_dict={}
					rs_json_data_dict["title"]=rs_json_data["title"]
					rs_json_data_dict["getChannelName"]=rs_json_data["getChannelName"]
					rs_json_data_dict["status"] = status_name_dict[str(rs_json_data["status"])]
					rs_json_data_dict["mobile"]=rs_json_data["mobile"]+"\t"
					rs_json_data_dict["getTime"]=rs_json_data["getTime"]
					rs_json_data_dict["useStartTime"]=rs_json_data["useStartTime"]
					rs_json_data_dict["useEndTime"]=rs_json_data["useEndTime"]
					csv_data.append(rs_json_data_dict)
	try:
		with open(csv_filename, "w", newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			#dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_name)
	except:
		with open(csv_sec_filename, "w", newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			#dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_sec_name)

#通过ID读取门店名称
def get_store_name_byid(storeid):
	G_Url="https://center.beyonds.com/merchant/merchant/v1/back/store/stores"
	G_Refer="http://center.beyonds.com/web/"
	params_dict={}
	params_dict["storeName"]=""
	params_dict["storeStatus"] =""
	params_dict["traderType"]=""
	params_dict["traderName"]=""
	params_dict["isValid"]=""
	params_dict["isBalance"]=""
	params_dict["plazaName"]=""
	params_dict["storeId"]=storeid
	params_dict["wechatMerchantType"]=""
	params_dict["status"]=""
	params_dict["pageNo"]="1"
	params_dict["pageSize"]="10"
	params_dict["timestr"]=str(int(time.time())*1000)
	rs=webRequest("get",G_Url,G_Refer,params_dict,"")
	if int(rs.status_code)==200:
		rs_json=json.loads(rs.text)
		if rs_json["data"]["items"][0]["storeName"] != None:
			store_name=rs_json["data"]["items"][0]["storeName"]
		else:
			store_name=None
	return store_name

#读取门店列表
def get_store_list(self):
	#读取门店信息
	G_maxrecord=0
	G_maxpage=0
	G_Url="https://center.beyonds.com/merchant/merchant/v1/back/store/stores"
	G_Refer="http://center.beyonds.com/web/"
	store_status_index_dict={"0":"","1":"1","2":"0","3":"2"}
	store_status_dict={"0":"已失效","1":"已生效","2":"已废止"}
	balance_status_index_dict={"0":"","1":"1","2":"0"}
	balance_status_dict={"0":"不可结算","1":"可结算","2":"不可结算"}
	traderType_dict={"1":"企业","2":"个体"}
	wechatType={"1":"丙晟服务商子商户微信号","2":"第三方服务商子商户微信号","3":"个人微信号","0":"未签约验证"}
	params_dict= {}
	params_dict["storeName"]=""
	params_dict["storeStatus"] = store_status_index_dict[str(self.sel_store_vaild_status.currentIndex())]
	params_dict["traderType"]=""
	params_dict["traderName"]=""
	params_dict["isValid"]=""
	params_dict["isBalance"]=balance_status_index_dict[str(self.sel_store_balance_status.currentIndex())]
	params_dict["plazaName"]=""
	params_dict["storeId"]=""
	params_dict["wechatMerchantType"]=""
	params_dict["status"]=""
	params_dict["pageNo"]="1"
	params_dict["pageSize"]="50"
	params_dict["timestr"]=str(int(time.time())*1000)
	#print(params_dict)
	csv_title=["storeId","storeName","contacts","traderName","traderType","mobile","bunkNo","businessName",
			   "sourceName","plazaName","isBalance","storeStatus","wechatMerchantType","paymentSataus","updateTime"]
	csv_path=get_desktop()
	csv_name="门店列表.csv"
	csv_sec_name="门店列表"+str(int(time.time()))+".csv"
	csv_filename=os.path.join(csv_path,csv_name)
	csv_sec_filename=os.path.join(csv_path,csv_sec_name)
	csv_data=[]
	csv_data.append({"storeId":"门店ID","storeName":"门店名称","contacts":"门店联系人","traderName":"商户名称","traderType":"商户类型",
					 "mobile":"登陆手机号码","bunkNo":"铺位号","businessName":"业态","sourceName":"门店来源","plazaName":"广场",
					 "isBalance":"门店类型","storeStatus":"门店状态","wechatMerchantType":"微信商户类型","paymentSataus":"买单开通状态",
					 "updateTime":"更新时间"})
	rs=webRequest("get",G_Url,G_Refer,params_dict,"")
	rs_json=json.loads(rs.text)
	G_maxpage=rs_json["data"]["totalPages"]
	G_maxrecord=rs_json["data"]["totalCount"]
	self.statusBar().showMessage("开始导出门店列表，请稍后")
	self.info_progressbar.setRange(0,G_maxrecord)
	self.info_lable.setText("共找到"+str(G_maxrecord)+"条记录，共"+str(G_maxpage)+"页")
	QApplication.processEvents()
	csv_row=0
	for ipage in range(G_maxpage):
		params_dict["pageNo"]=str(ipage+1)
		rs=webRequest("get",G_Url,G_Refer,params_dict,"")
		rs_json=json.loads(rs.text)
		for rs_json_data in rs_json["data"]["items"]:
			csv_row+=1
			self.info_progressbar.setValue(csv_row)
			QApplication.processEvents()
			rs_json_data_dict=collections.OrderedDict()
			rs_json_data_dict["storeId"]=rs_json_data["storeId"]
			#print(rs_json_data["storeName"])
			rs_json_data_dict["storeName"]=rs_json_data["storeName"]
			rs_json_data_dict["contacts"]=rs_json_data["contacts"]
			rs_json_data_dict["traderName"]=rs_json_data["traderName"]
			if rs_json_data["traderType"] != None:
				rs_json_data_dict["traderType"]=traderType_dict[str(rs_json_data["traderType"])]
			else:
				rs_json_data_dict["traderType"]="-"
			rs_json_data_dict["mobile"]=rs_json_data["mobile"]+"\t"
			rs_json_data_dict["bunkNo"] = rs_json_data["bunkNo"]+"\t"
			rs_json_data_dict["businessName"] = rs_json_data["businessName"]
			rs_json_data_dict["sourceName"] = rs_json_data["sourceName"]
			rs_json_data_dict["plazaName"] = rs_json_data["plazaName"]
			rs_json_data_dict["isBalance"] = balance_status_dict[str(rs_json_data["isBalance"])]
			# isvaild=0 已废止 isvalid=1 且 status=0 已失效 status=1 已生效
			if str(rs_json_data["isValid"])=="0":
				rs_json_data_dict["storeStatus"] = "已废止"
			elif str(rs_json_data["isValid"])=="1":
				if str(rs_json_data["status"])=="1":
					rs_json_data_dict["storeStatus"] = "已生效"
				elif str(rs_json_data["status"])=="0":
					rs_json_data_dict["storeStatus"] = "已失效"
			if rs_json_data["wechatMerchantType"] != None:
				rs_json_data_dict["wechatMerchantType"] = wechatType[str(rs_json_data["wechatMerchantType"])]
			else:
				rs_json_data_dict["wechatMerchantType"]="-"
			rs_json_data_dict["updateTime"]=rs_json_data["updateTime"]
			csv_data.append(rs_json_data_dict)
	#读取买单开通门店列表，反向更新dict
	pay_storeid_data=get_payment_list(self)
	#print(pay_storeid_data)
	csv_data_list=[]
	csv_data_node=collections.OrderedDict()
	for csv_data_node in csv_data:
		src_storeid=str(csv_data_node["storeId"])
		for pay_storeid_dict in pay_storeid_data:
			pay_store_name=pay_storeid_dict["name"]
			pay_store_type_list=pay_storeid_dict["list"]
			if pay_store_type_list:
				if src_storeid in pay_store_type_list:
					csv_data_node["paymentSataus"]=pay_store_name
					self.statusBar().showMessage("正在更新买单门店状态，请稍等")
					QApplication.processEvents()
					break
	try:
		with open(csv_filename, "w", newline="") as datacsv:
			# dwrite = csv.writer(datacsv)
			# dwrite.writerows(csv_data_list)
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			#dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_name)
	except:
		with open(csv_sec_filename, "w", newline="") as datacsv:
			# dwrite = csv.writer(datacsv)
			# dwrite.writerows(csv_data_list)
			dwrite = csv.DictWriter(datacsv, fieldnames=csv_title)
			#dwrite.writeheader()
			dwrite.writerows(csv_data)
			self.statusBar().showMessage("数据已成功导出在桌面，文件名为：" + csv_sec_name)

#读取买单门店列表
def get_payment_list(self):
	G_maxrecord=0
	G_maxpage=0
# 待审核
# https://center.beyonds.com/merchant/merchant/v1/back/pay/query?plazaName=&p=1&ps=100&type=2&orderStatus=0&storeId=&timestr=1589722939091
# 已开通
# https://center.beyonds.com/merchant/merchant/v1/back/pay/query?plazaName=&p=1&ps=100&type=2&contractStatus=1&storeId=&timestr=1589723152834
# 未签约
# https://center.beyonds.com/merchant/merchant/v1/back/pay/query?plazaName=&p=1&ps=100&type=2&contractStatus=0&storeId=&timestr=1589723191215
# 已驳回
# https://center.beyonds.com/merchant/merchant/v1/back/pay/query?plazaName=&p=1&ps=100&type=2&orderStatus=2&storeId=&timestr=1589723216801
# 已停用
# https://center.beyonds.com/merchant/merchant/v1/back/pay/query?plazaName=&p=1&ps=100&type=2&contractStatus=2&storeId=&timestr=1589723241099
	G_Url="https://center.beyonds.com/merchant/merchant/v1/back/pay/query"
	G_Refer="https://center.beyonds.com/web/"
	pay_store_data=[]
	params_dict={}
	params_dict["plazaName"]=""
	params_dict["p"]="1"
	params_dict["ps"]="100"
	params_dict["type"]="2"
	params_dict["storeId"]=""
	payment_headlist=[{"name":"待审核","orderStatus":"0","contractStatus":None},
					  {"name":"已开通","orderStatus":None,"contractStatus":"1"},
					  {"name":"未签约","orderStatus":None,"contractStatus":"0"},
					  {"name":"已驳回","orderStatus":"2","contractStatus":None},
					  {"name":"已停用","orderStatus":None,"contractStatus":"2"}]
	for payment_headlist_node in payment_headlist:
		pay_store_name=payment_headlist_node["name"]
		#print(pay_store_name)
		self.statusBar().showMessage("开始加载买单"+pay_store_name+"的数据，请稍等")
		QApplication.processEvents()
		params_dict["contractStatus"]=payment_headlist_node["contractStatus"]
		params_dict["orderStatus"]=payment_headlist_node["orderStatus"]
		params_dict["timestr"]=str(int(time.time()*1000))
		pay_store_dict={}
		pay_storeid_list= []
		rs=webRequest("get",G_Url,G_Refer,params_dict,"")
		if int(rs.status_code)==200:
			rs_json=json.loads(rs.text)
			G_maxrecord=int(rs_json["data"]["totalCount"])
			G_maxpage=int(rs_json["data"]["totalPages"])
			#self.info_label.setText("共"+str(G_maxrecord)+"条记录，共"+str(G_maxpage)+"页")
			if G_maxrecord>0:
				for ipage in range(G_maxpage):
					params_dict["p"] = str(ipage+1)
					rs=webRequest("get",G_Url,G_Refer,params_dict,"")
					rs_json=json.loads(rs.text)
					for rs_json_data in rs_json["data"]["items"]:
						storeid=rs_json_data["storeId"]
						if storeid not in pay_storeid_list:
							pay_storeid_list.append(str(storeid))
		pay_store_dict["name"]=pay_store_name
		pay_store_dict["list"]=pay_storeid_list
		pay_store_data.append(pay_store_dict)
	return pay_store_data

#备份各门店的头图信息
def get_Store_image_backup(self,filename):
	ps = requests.session()
	G_Url = "https://center.beyonds.com/xmtxapib/apiStoreDecorate/v1/findStoreDecorateList"
	G_Refer="https://center.beyonds.com/xmt/"
	perPage = 50
	post_data = {}
	post_data["pageCount"]=0
	post_data["pageSize"]=10
	post_data["id"]=""
	post_data["title"]=""
	post_data["storeId"]=""
	post_data["tag"]=""
	post_data["applicationModule"]=""
	post_data["paySwitch"]=""
	post_data["queueSwitch"]=""
	json_store_post_data = json.dumps(post_data)
	#print(json_store_post_data)
	rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
	json_store_data=json.loads(rs.text)
	#print(json_store_data)
	G_maxrecord = json_store_data["data"]["total"]
	G_maxpage = math.ceil(G_maxrecord/perPage) #向上取整，算页数
	self.info_progressbar.setRange(0,G_maxpage-1)
	#print(G_maxrecord)
	store_list_header=['id','name','node']
	store_list_data=[]
	for ipage in range(G_maxpage):
		post_data["pageCount"]=ipage
		self.info_progressbar.setValue(ipage)
		QApplication.processEvents()
		post_data["pageSize"]=perPage
		json_store_post_data = json.dumps(post_data)
		rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
		json_store_data = json.loads(rs.text)
		#print(json_store_data)
		for json_store_param in json_store_data["data"]["storeDecorateVOList"]:
			store_list_data_temp={}
			store_list_data_temp["id"]=json_store_param["id"]
			store_list_data_temp["name"]=json_store_param["title"]
			#self.stb_info.showMessage("正在导出"+json_store_param["title"]+"的图片路径")
			store_list_data_temp["node"]=json_store_param["headImage"]
			store_list_data.append(store_list_data_temp)
			#print(store_id+","+store_name)
	#print(store_list_data)
	try:
		with open(filename,"w",newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv,fieldnames=store_list_header)
			dwrite.writeheader()
			dwrite.writerows(store_list_data)
	except:
		filename="store_back"+str(int(time.time()))+".csv"
		with open(filename, "w", newline="") as datacsv:
			dwrite = csv.DictWriter(datacsv, fieldnames=store_list_header)
			dwrite.writeheader()
			dwrite.writerows(store_list_data)
	self.stb_info.showMessage("门店图片信息备份成功")

def get_proxy(self):
	http_proxy={}
	if self.chb_proxy.isChecked():
		http_proxy["isused"]=True
		http_proxy["username"]=self.tx_proxy_username.text()
		http_proxy["password"]=self.tx_proxy_password.text()
	else:
		http_proxy["isused"]=False
		http_proxy["username"]=""
		http_proxy["password"]=""
	return http_proxy

def wmEvent_image_del(self):
	os_path=get_desktop()
	fileName_choose = QFileDialog.getOpenFileName(self,"选取文件",os_path,  # 起始路径
												"Image Files(*.jpg *.png)")
	if fileName_choose != "":
		valid_dict=isValidImage(fileName_choose)
		if valid_dict["isimage"]==False:
			QtWidgets.QMessageBox.about(self,"错误信息","选中的不是有效的图片文件")
		else:
			#获取代理
			http_proxy=get_proxy(self)
			#先备份图片并保存到store_backup.csv中
			get_Store_image_backup(self,"store_del_backup.csv.csv")
			#然后执行删除操作
			filename=valid_dict["filename"]
			post_image_del(self,filename,http_proxy)
	else:
		self.stb_info.showMessage("未选择文件")

def wmEvent_image_resume(self):
	box=QtWidgets.QMessageBox()
	box.setWindowTitle("操作提示")
	box.setText("选择还原到删除前还是新增前?")
	box.setStandardButtons(QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No|QtWidgets.QMessageBox.Cancel)
	add_button=box.button(QtWidgets.QMessageBox.Yes)
	add_button.setText("新增前")
	del_button=box.button(QtWidgets.QMessageBox.No)
	del_button.setText("删除前")
	can_button=box.button(QtWidgets.QMessageBox.Cancel)
	can_button.setText("取消选择")
	box.exec_()
	if box.clickedButton()==add_button:
		post_image_resume(self,"store_add_back.csv")
	elif box.clickedButton()==del_button:
		post_image_resume(self,"store_del_back.csv")
	else:
		pass

def wmEvent_image_add(self):
	os_path=get_desktop()
	fileName_choose = QFileDialog.getOpenFileName(self,"选取文件",os_path,  # 起始路径
												"Image Files(*.jpg *.png)")
	if fileName_choose != "":
		valid_dict = isValidImage(fileName_choose)
		if valid_dict["isimage"]==False:
			QtWidgets.QMessageBox.about(self,"错误信息","选中的不是有效的图片文件")
		else:
			#获取代理
			http_proxy=get_proxy(self)
			#
			get_Store_image_backup(self,"store_add_backup.csv")
			# 然后执行删除操作
			filename = valid_dict["filename"]
			post_image_add(self,filename,http_proxy)
	else:
		self.stb_info.showMessage("未选择文件")

def post_image_resume(self,filename):
	#pdb.set_trace()
	if os.path.exists(filename) ==False:
		QtWidgets.QMessageBox.about(self,"错误信息","该文件不存在，无法进行恢复处理")
		return
	else:
		store_list_data=[]
		#从csv文件中取出门店数据，并且存在dirct，再将dirct保存进list
		store_update_url="https://center.beyonds.com/xmtxapib/apiXMT/proxy/xmtm//v1/storeDecorate/update"
		store_update_Refer="https://center.beyonds.com/xmt/"
		with open("log_image_resume.txt","w") as wr:
			wr.write("开始恢复门店图片：\n")
		with open(filename, "r") as csvFile:
			dict_read = csv.DictReader(csvFile)
			for row in dict_read:
				store_list_param={}
				store_list_param["id"]=row["id"]
				store_list_param["name"]=row["name"]
				store_list_param["node"]=row["node"]
				store_list_data.append(store_list_param)
			csvFile.close()
		ps = requests.session()
		G_Url = "https://center.beyonds.com/xmtxapib/apiStoreDecorate/v1/findStoreDecorateList"
		G_Refer="https://center.beyonds.com/xmt/"
		perPage = 50
		post_data = {}
		post_data["pageCount"]=0
		post_data["pageSize"]=10
		post_data["id"]=""
		post_data["title"]=""
		post_data["storeId"]=""
		post_data["tag"]=""
		post_data["applicationModule"]=""
		post_data["paySwitch"]=""
		post_data["queueSwitch"]=""
		json_store_post_data = json.dumps(post_data)
		#print(json_store_post_data)
		rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
		json_store_data = json.loads(rs.text)
		#print(json_store_data)
		G_maxrecord = json_store_data["data"]["total"]
		G_maxpage = math.ceil(G_maxrecord/perPage) #向上取整，算页数
		#print(G_maxrecord)
		store_list_json_data=[]
		self.stb_info.showMessage("正在加载门店信息")
		self.info_progressbar.setRange(0,G_maxpage-1)
		for ipage in range(G_maxpage):
			post_data["pageCount"]=ipage
			post_data["pageSize"]=perPage
			self.info_progressbar.setValue(ipage)
			QApplication.processEvents()
			json_store_post_data = json.dumps(post_data)
			#print(ipage)
			rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
			json_store_data = json.loads(rs.text)
			for json_store_param in json_store_data["data"]["storeDecorateVOList"]:
				store_list_json_data.append(json_store_param)
		#双循环开始
		self.stb_info.showMessage("开始还原门店图片信息")
		self.info_progressbar.setRange(0, len(store_list_data))
		row=0
		for store_node in store_list_data:
			self.info_progressbar.setValue(row+1)
			QApplication.processEvents()
			store_node_id = store_node["id"]
			store_node_name = store_node["name"]
			store_node_image = store_node["node"]
			for json_store_node in store_list_json_data:
				if store_node_id == json_store_node["id"]:
					#pdb.set_trace()
					self.stb_info.showMessage("当前正在还原"+store_node_name+"的图片信息")
					QApplication.processEvents()
					json_store_node["headImage"]=store_node_image
					json_store_node_dump = json.dumps(json_store_node)
					print(store_node_image)
					store_update_url="https://center.beyonds.com/xmtxapib/apiXMT/proxy/xmtm//v1/storeDecorate/update"
					store_update_Refer="https://center.beyonds.com/xmt/"
					rs = webRequest("post",store_update_url,store_update_Refer,json_store_node_dump,"")
					with open("log_image_resume.txt","a+") as wr:
						wr.write(store_node_name+"更新了头图\n")
						wr.flush()
						pass
					#print(rs)
		self.stb_info.showMessage("门店图片复原成功")

#新增图片
def post_image_add(self,filename,http_proxy_dict):
	#读取本地图片，并转化为ahash值
	src_image = Image.open(filename)
	#先行获取所有门店的ID
	ps = requests.session()
	G_Url = "https://center.beyonds.com/xmtxapib/apiStoreDecorate/v1/findStoreDecorateList"
	G_Refer="https://center.beyonds.com/xmt/"
	perPage = 50
	post_data = {}
	post_data["pageCount"]=0
	post_data["pageSize"]=10
	post_data["id"]=""
	post_data["title"]=""
	post_data["storeId"]=""
	post_data["tag"]=""
	post_data["applicationModule"]=""
	post_data["paySwitch"]=""
	post_data["queueSwitch"]=""
	json_store_post_data = json.dumps(post_data)
	#print(json_store_post_data)
	rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
	json_store_data = json.loads(rs.text)
	#print(json_store_data)
	G_maxrecord = json_store_data["data"]["total"]
	G_maxpage = math.ceil(G_maxrecord/perPage) #向上取整，算页数
	self.info_progressbar.setRange(0,G_maxpage)
	QApplication.processEvents()
	#print(G_maxrecord)
	with open("log_image_add.txt","w+") as wr:
		wr.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		wr.write("开始批量更换头图:\n")
	store_list_data=[]
	for ipage in range(G_maxpage):
		self.stb_info.showMessage("正在将门店信息完整载入列表")
		self.info_progressbar.setValue(ipage)
		QApplication.processEvents()
		post_data["pageCount"]=ipage
		post_data["pageSize"]=perPage
		json_store_post_data = json.dumps(post_data)
		#print(ipage)
		rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
		json_store_data = json.loads(rs.text)
		for json_store_param in json_store_data["data"]["storeDecorateVOList"]:
			store_list_data.append(json_store_param)
	#获取每个店铺的json节点，直接修改提交
	row=0
	self.info_progressbar.setRange(0,len(store_list_data))
	for json_store_param in store_list_data:
		#print("--------------数据分割线--------------")
		#print(json_store_param)
		#提取head图片
		self.info_progressbar.setValue(row+1)
		storeName = json_store_param["title"]
		self.stb_info.showMessage("正在对比"+storeName+"的图片信息")
		QApplication.processEvents()
		#print(storeName)
		headimage = json_store_param["headImage"]
		#转为List
		headlist = headimage.split(",")
		#print(headimage)
		b_same_image = False
		if headimage!="":
			for list_data in headlist:
				#提取图片url
				if list_data=="":
					headlist.remove(list_data)
					b_same_image = (False or b_same_image)
				else:
					imageurl = list_data.replace("https://","").replace("http://","")
					imageurl = "https://"+imageurl
					#print("开始下载"+imageurl)
					deb_image = getImageByUrl(imageurl,http_proxy_dict)
					#两图片对比hash值，判断相似度
					cosin=image_sim(src_image,deb_image)
					print("图片相似度:",cosin)
					if cosin>=1:
						#print("找到相同图片，调整顺序")
						self.stb_info.showMessage("在" + storeName + "的图片信息中找到相同图片")
						QApplication.processEvents()
						b_same_image = (True or b_same_image)
						#从list删除该项
						headlist.remove(list_data)
						#将该项插入第一个位置
						headlist.insert(0,list_data)
						#print(headlist)
						break
					else:
						b_same_image = (False or b_same_image)
		else:
			#print(storeName+"未发现头图")
			self.stb_info.showMessage("在" + storeName + "的图片信息中未找到相同图片")
			QApplication.processEvents()
			b_same_image = False
		#print(b_same_image)
		if b_same_image == False:
			#print("开始新增头图")
			self.stb_info.showMessage("开始为"+storeName+"新增图片,并调整图片顺序")
			QApplication.processEvents()
			image_add_url="https://center.beyonds.com/mdrz/mdrz/common/upload"
			image_add_Refer ="https://center.beyonds.com/xmt"
			rs = PostImage(image_add_url,image_add_Refer,filename)
			imageurl = rs["data"]["Location"]
			imageurl = imageurl.replace("https://","").replace("http://","")
			imageurl = "https://"+imageurl
			headlist.insert(0,imageurl)
			#print(headlist)
		else:
			pass
		#头图列表转为字符串
		splitchar=","
		new_headimage = splitchar.join(image_temp for image_temp in headlist)
		if new_headimage==headimage:
			#print("不需要更新顺序")
			with open("log_image_add.txt","a+") as wr:
				wr.write(storeName+"图片存在且是第一位，未更新\n")
				wr.flush()
				continue
		else:
			if new_headimage.endswith(","):
				new_headimage = new_headimage[:-1]
			json_store_param["headImage"]=new_headimage
			#print(new_headimage)
			#将json节点修改后重新提交数据
			store_update_url="https://center.beyonds.com/xmtxapib/apiXMT/proxy/xmtm//v1/storeDecorate/update"
			store_update_Refer="https://center.beyonds.com/xmt/"
			store_update_json=json.dumps(json_store_param)
			#print(store_update_json)
			rs = webRequest("post",store_update_url,store_update_Refer,store_update_json,"")
			if int(rs.status_code)==200:
				self.stb_info.showMessage(storeName+"图片更新成功")
				QApplication.processEvents()
			with open("log_image_add.txt","a+") as wr:
				wr.write(storeName+"更新了头图\n")
				wr.flush()
				pass

#移除相同的图片
def post_image_del(self,filename,http_proxy_dict):
	#读取本地图片，并转化为ahash值
	src_image = Image.open(filename)
	#sr_image_hash = aHash(sr_image)
	ps = requests.session()
	G_Url = "https://center.beyonds.com/xmtxapib/apiStoreDecorate/v1/findStoreDecorateList"
	G_Refer="https://center.beyonds.com/xmt/"
	perPage = 50
	post_data = {}
	post_data["pageCount"]=0
	post_data["pageSize"]=10
	post_data["id"]=""
	post_data["title"]=""
	post_data["storeId"]=""
	post_data["tag"]=""
	post_data["applicationModule"]=""
	post_data["paySwitch"]=""
	post_data["queueSwitch"]=""
	json_store_post_data = json.dumps(post_data)
	#print(json_store_post_data)
	rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
	json_store_data=json.loads(rs.text)
	G_maxrecord = json_store_data["data"]["total"]
	G_maxpage = math.ceil(G_maxrecord/perPage) #向上取整，算页数
	self.info_progressbar.setRange(0,G_maxpage)
	QApplication.processEvents()
	#print(G_maxrecord)
	with open("log_image_del.txt","w+") as wr:
		wr.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		wr.write("开始批量删除头图:\n")
	#将所有的门店节点都读取到列表中
	store_list_data=[]
	for ipage in range(G_maxpage):
		self.info_progressbar.setValue(ipage)
		QApplication.processEvents()
		post_data["pageCount"]=ipage
		post_data["pageSize"]=perPage
		json_store_post_data = json.dumps(post_data)
		#print(ipage)
		rs = webRequest("post",G_Url,G_Refer,json_store_post_data,"store_list")
		json_store_data = json.loads(rs.text)
		for json_store_param in json_store_data["data"]["storeDecorateVOList"]:
			store_list_data.append(json_store_param)
	#开始每节点删除
	self.info_progressbar.setRange(0,len(store_list_data))
	print(len(store_list_data))
	QApplication.processEvents()
	row=0
	for json_store_param in store_list_data:
		#print("--------------数据分割线--------------")
		storeName = json_store_param["title"]
		#print(storeName)
		headimage = json_store_param["headImage"]
		#print(headimage)
		row=row+1
		#转为List
		print(row,len(store_list_data))
		self.stb_info.showMessage("开始对比"+storeName+"的图片信息")
		self.info_progressbar.setValue(row)
		QApplication.processEvents()
		if headimage != "":
			headlist = headimage.split(",")
			oldlength=len(headlist)
			#print("找到"+str(len(headlist))+"张图片")
			#pdb.set_trace()
			for list_data in headlist:
				cosin = 0
				imageurl = list_data.replace("https://","").replace("http://","")
				imageurl = "https://"+imageurl
				try:
					#print("开始读取图片",imageurl)
					# 写入temp.jpg文件
					#pdb.set_trace()
					deb_image = getImageByUrl(imageurl,http_proxy_dict)
					#两图片对比hash值，判断相似度
					cosin = image_sim(src_image,deb_image)
					#time.sleep(1)
					#print("图片相似度:",cosin)
					self.stb_info.showMessage("当前图片与目标图片相似度为:"+str(cosin))
					QApplication.processEvents()
				except:
					if list_data == "":
						cosin=1
				if cosin>=1:
					headlist.remove(list_data)
					#print("移除该图片")
				else:
					pass
			newlength=len(headlist)
			if len(headlist)>0:
				splitchar=","
				new_headimage = splitchar.join(image_temp for image_temp in headlist)
			else:
				new_headimage = ""
		#print(new_headimage)
		if new_headimage != headimage:
			with open("log_image_del.txt","a+") as wr:
				wr.write(storeName+"发现相同图片，删除指定图片\n")
				wr.write(storeName+"目前有"+str(newlength)+"张图片\n")
			if new_headimage.endswith(","):
				new_headimage = new_headimage[:-1]
			json_store_param["headImage"]=new_headimage
			#将json节点修改后重新提交数据
			store_update_url="https://center.beyonds.com/xmtxapib/apiXMT/proxy/xmtm//v1/storeDecorate/update"
			store_update_Refer="https://center.beyonds.com/xmt/"
			store_update_json=json.dumps(json_store_param)
			rs = webRequest("post",store_update_url,store_update_Refer,store_update_json,"")
		else:
			with open("log_image_del.txt","a+") as wr:
				wr.write(storeName+"未发现指定图片\n")
				wr.write(storeName+"目前有"+str(newlength)+"张图片\n")
	self.stb_info.showMessage("图片删除已完成，请查看日志")


def get_fq_data(bdate,edate,codelist):
	G_maxrecord=0
	G_Url = "https://center.beyonds.com/coupon/inner/user/coupons/codes"
	G_Refer = "https://center.beyonds.com/web/"
	params_dict={}
	params_dict["pageIndex"]="1"
	params_dict["pageSize"]="10"
	params_dict["getStartTime"]=bdate
	params_dict["getEndTime"]=edate
	params_dict["plazaId"]=G_List["orgCode"]
	code_list=codelist.split(",")
	for code_node in code_list:
		params_dict["no"]=code_node
		params_dict["timestr"]=str(int(time.time()*1000))
		rs=webRequest("get",G_Url,G_Refer,params_dict,"")
		if int(rs.status_code)==200:
			rs_json=json.loads(rs.text)
			G_maxrecord+=int(rs_json["data"]["totalSize"])
	return G_maxrecord

def get_hx_data(bdate,edate,codelist):
	G_maxrecord=0
	G_Url = "https://center.beyonds.com/coupon/inner/user/coupons/certificate-codes"
	G_Refer = "https://center.beyonds.com/web/"
	params_dict={}
	params_dict["pageIndex"]="1"
	params_dict["pageSize"]="10"
	params_dict["usedStartTime"]=bdate
	params_dict["usedEndTime"]=edate
	params_dict["plazaId"]=G_List["orgCode"]
	code_list=codelist.split(",")
	for code_node in code_list:
		params_dict["no"]=code_node
		params_dict["timestr"]=str(int(time.time()*1000))
		rs=webRequest("get",G_Url,G_Refer,params_dict,"")
		if int(rs.status_code)==200:
			rs_json=json.loads(rs.text)
			G_maxrecord+=int(rs_json["data"]["totalSize"])
	return G_maxrecord

def get_group_data(self):
	# 确定计算模型
	if self.rb_hx_type_max.isChecked():
		bl_Calc=True
	if self.rb_hx_type_real.isChecked():
		bl_Calc=False
	grp1_name=self.tx_hx_grp1_name.text()
	grp2_name=self.tx_hx_grp2_name.text()
	grp1_max=self.tx_hx_grp1_max.text()
	grp2_max=self.tx_hx_grp2_max.text()
	grp1_code=self.tx_hx_grp1_codelist.text()
	grp2_code=self.tx_hx_grp2_codelist.text()
	bdate=self.sel_begindate.date().toString("yyyy-MM-dd")+" 00:00:00"
	edate=self.sel_enddate.date().toString("yyyy-MM-dd")+" 23:59:59"
	#计算时间差
	bdatetime=datetime.datetime.strptime(bdate,"%Y-%m-%d %H:%M:%S")
	edatetime=datetime.datetime.strptime(edate,"%Y-%m-%d %H:%M:%S")
	nday=(edatetime-bdatetime).days+1
	#print(nday)
	try:
		int_grp1_max=int(grp1_max)*nday
		int_grp2_max=int(grp2_max)*nday
	except:
		QtWidgets.QMessageBox.about(self,"错误提示","输入的最大金额有误，请修改")
		return
	#读取领取和核销的数据
	grp1_fqcnt=get_fq_data(bdate,edate,grp1_code)
	self.statusBar().showMessage("查找"+grp1_name+"发券数据")
	grp2_fqcnt=get_fq_data(bdate,edate,grp2_code)
	self.statusBar().showMessage("查找" + grp2_name + "发券数据")
	grp1_hxcnt=get_hx_data(bdate,edate,grp1_code)
	self.statusBar().showMessage("查找" + grp1_name + "核销数据")
	grp2_hxcnt=get_hx_data(bdate,edate,grp2_code)
	self.statusBar().showMessage("查找" + grp2_name + "核销数据")
	sendmessage=[]
	#插入信息头
	if self.sel_begindate.date()==self.sel_enddate.date():
		All_info=G_List["orgName"]+self.sel_begindate.date().toString("yyyy-MM-dd")+"的领取和核销记录如下:"
	else:
		All_info = G_List["orgName"] + self.sel_begindate.date().toString("yyyy-MM-dd")+"到"+self.sel_enddate.date().toString("yyyy-MM-dd") + "的领取和核销记录如下:"
	sendmessage.append(All_info)
	#统计第一组数据
	All_info=grp1_name+"共领取【"+str(grp1_fqcnt)+"】张,领取率【"+str('{:.2f}%'.format(grp1_fqcnt/int_grp1_max*100))+"】"
	sendmessage.append(All_info)
	if bl_Calc:
		All_info=grp1_name+"共核销【"+str(grp1_hxcnt)+"】张,核销率【"+str('{:.2f}%'.format(grp1_hxcnt/int_grp1_max*100))+"】"
	else:
		All_info = grp1_name+"共核销【"+str(grp1_hxcnt)+"】张,核销率【"+str('{:.2f}%'.format(grp1_hxcnt/grp1_fqcnt*100))+"】"
	sendmessage.append(All_info)
	#统计第二组数据
	All_info=grp2_name+"共领取【"+str(grp2_fqcnt)+"】张,领取率【"+str('{:.2f}%'.format(grp2_fqcnt/int_grp2_max*100))+"】"
	sendmessage.append(All_info)
	if bl_Calc:
		All_info=grp2_name+"共核销【"+str(grp2_hxcnt)+"】张,核销率【"+str('{:.2f}%'.format(grp2_hxcnt/int_grp2_max*100))+"】"
	else:
		All_info=grp2_name+"共核销【"+str(grp2_hxcnt)+"】张,核销率【"+str('{:.2f}%'.format(grp2_hxcnt/grp2_fqcnt*100))+"】"
	sendmessage.append(All_info)
	#统计累计
	All_info="累计领取【"+str(grp1_fqcnt+grp2_fqcnt)+"】张,总领取率【"+str('{:.2f}%'.format((grp1_fqcnt+grp2_fqcnt)/(int_grp1_max+int_grp2_max)*100))+"】"
	sendmessage.append(All_info)
	if bl_Calc:
		All_info="累计核销【"+str(grp1_hxcnt+grp2_hxcnt)+"】张,总核销率【"+str('{:.2f}%'.format((grp1_hxcnt+grp2_hxcnt)/(int_grp1_max+int_grp2_max)*100))+"】"
	else:
		All_info="累计核销【"+str(grp1_hxcnt+grp2_hxcnt)+"】张,总核销率【"+str('{:.2f}%'.format((grp1_hxcnt+grp2_hxcnt)/(grp1_fqcnt+grp2_fqcnt)*100))+"】"
	sendmessage.append(All_info)
	sp="\n"
	All_info=sp.join(sendmessage)
	pyperclip.copy(All_info)
	QtWidgets.QMessageBox.about(self,"结果提示",All_info+"\n\n此消息已自动复制到剪切板")

#交易订单查询
#筛选条件:
#订单类型：全部{productType="",orderType=None},买单直连{productType:pay_direct,orderType:None},买单延时分账{productType:pay_delay,orderType:None}
#门店直送订单-券商品{productType:coupon_goods,orderType:goods},门店直送订单-零售商品{productType:retail_goods,orderType:goods}
#门店直送订单-预售商品{productType:presale_goods,orderType:goods},门店直送订单-餐饮商品{productType:catering_goods,orderType:goods}
#用户自提-零售商品{productType:resale_goods,orderType:goods_self},门店直送订单-餐饮商品{productType:repast_goods,orderType:goods_self}
#
#订单状态： orderStatus
# 30：待付款  38：微信受理成功  40：付款成功  41：待接单  42：待发货  43：已发货  59：已拒收  50：交易成功/已签收/已确认  60：交易完成  70：交易关闭
#配送方式：deliveryType
#全部 “ “，系统发货：system，商户自行发货：customer
def get_paydetail_list(self):
	#初始化订单字典
	pay_type=[{"index":"0","productType":"","orderType":None},{"index":"1","productType":"pay_direct","orderType":None},
			{"index":"2","productType":"pay_delay","orderType":None},{"index":"3","productType":"coupon_goods","orderType":"goods"},
			{"index":"4","productType":"retail_goods","orderType":"goods"},{"index":"5","productType":"presale_goods","orderType":"goods"},
			{"index":"6","productType":"catering_goods","orderType":"goods"},{"index":"7","productType":"resale_goods","orderType":"goods_self"},
			{"index":"8","productType":"repast_goods","orderType":"goods_self"}]
	pay_status=[{"index":"0","orderStatus":""},{"index":"1","orderStatus":"30"},{"index":"2","orderStatus":"38"},{"index":"3","orderStatus":"40"},
				{"index":"4","orderStatus":"41"},{"index":"5","orderStatus":"42"},{"index":"6","orderStatus":"43"},{"index":"7","orderStatus":"59"},
				{"index":"8","orderStatus":"50"},{"index":"9","orderStatus":"60"},{"index":"10","orderStatus":"70"}]
	#send_type=[{"index":"0","deliveryType":""},{"index":"1","deliveryType":"system"},{"index":"2","deliveryType":"customer"}]
	cphone=self.tx_pay_phone.text()
	store_id = self.tx_pay_storeid.text()
	if store_id != "":
		store_name=urllib.parse.quote(get_store_name_byid(store_id))
		if store_name!=None:
			store_con=store_name.strip()+" ("+store_id+")"
		else:
			QtWidgets.QMessageBox.about(self,"错误提示","不是有效的门店ID，只能查询已生效的门店")
			return
	else:
		store_id=""
		store_con=""
	#组合查询条件
	G_Url="https://center.beyonds.com/xmtxapib/apiOrder/getOrderList"
	G_Refer="https://center.beyonds.com/xmt/"
	params_dict={}
	params_dict["pageNum"]="1"
	params_dict["limit"]="50"
	params_dict["orderNo"]=""
	params_dict["phoneNo"]=cphone
	params_dict["memberId"]=""
	#订单状态
	pay_status_index=self.sel_pay_paystatus.currentIndex()
	params_dict["orderStatus"]=""
	for pay_status_node in pay_status:
		if int(pay_status_node["index"])==pay_status_index:
			params_dict["orderStatus"]=pay_status_node["orderStatus"]
			break
	params_dict["orderChannelNo"]=""
	params_dict["payReqNo"]=""
	params_dict["storeId"]=store_id
	params_dict["storeName"]=store_con
	params_dict["deliveryType"]=""
	send_type_inde = self.sel_pay_sendtype.currentIndex()
	if send_type_inde==0:
		params_dict["deliveryType"] = ""
	elif send_type_inde==1:
		params_dict["deliveryType"] = "system"
	elif send_type_inde == 2:
		params_dict["deliveryType"] = "customer"
	bdate=self.sel_begindate.date().toString("yyyy-MM-dd")+" 00:00:00"
	edate=self.sel_enddate.date().toString("yyyy-MM-dd")+" 23:59:59"
	bdatetime=datetime.datetime.strptime(bdate,"%Y-%m-%d %H:%M:%S")
	edatetime=datetime.datetime.strptime(edate,"%Y-%m-%d %H:%M:%S")
	bux_time=int(round(time.mktime(bdatetime.timetuple())*1000))
	eux_time=int(round(time.mktime(edatetime.timetuple())*1000))
	params_dict["orderTradeTimeBegin"]=bux_time
	params_dict["orderTradeTimeEnd"]=eux_time
	params_dict["productType"]=None
	params_dict["orderType"]=None
	pay_type_index=self.sel_pay_paytype.currentIndex()
	for pay_type_node in pay_type:
		if int(pay_type_node["index"])==pay_type_index:
			params_dict["productType"]=pay_type_node["productType"]
			params_dict["orderType"]=pay_type_node["orderType"]
			break
	params_dict["timestr"]=str(int(time.time()*1000))
	#print(params_dict)
	#开始查询
	json_orderstates = {"10": "免密受理失败", "30": "待付款", "38": "微信受理成功", "40": "付款成功", "41": "待接单", "42": "待发货",
						"43": "已发货", "45": "红包发送中", "46": "红包发送失败", "50": "交易成功/已签收/已确认", "59": "已拒收", "60": "交易完成",
						"70": "交易关闭","71":"交易关闭"}
	json_ordertype = {"coupon": "优惠券订单", "park": "停车线上订单", "park_ex": "停车免密订单", "park_mix": "停车线上订单",
					  "wx_coupon": "微信代金券订单", "cps_coupon": "收券退款订单", "mc_bsc": "扫码收款订单", "pay_direct": "买单直连",
					  "checkout_order": "买单延时分账", "goods": "1", "goods_self": "1"}
	json_producttype = {"coupon_goods": "门店直送订单-券商品", "retail_goods": "门店直送订单-零售商品", "presale_goods": "门店直送订单-预售商品",
						"catering_goods": "门店直送订单-餐饮商品", "resale_goods": "用户自提-零售商品", "repast_goods": "用户自提-餐饮商品"}
	csv_data=[]
	csv_title = ["交易订单号", "商户订单号", "会员手机号", "会员ID", "微信openId", "交易订单状态", "下单时间", "门店ID", "门店名称", "支付方式", "支付单号",
				 "订单金额", "订单实付金额", "订单优惠金额", "交易订单类型", "配送方式"]
	csv_name="交易明细记录.csv"
	csv_sec_name="交易明细记录"+str(int(time.time()))+".csv"
	csv_path=get_desktop()
	csv_filename=os.path.join(csv_path,csv_name)
	csv_sec_filename=os.path.join(csv_path,csv_sec_name)
	rs=webRequest("get",G_Url,G_Refer,params_dict,"detail_list")
	if int(rs.status_code)==200:
		split = ","
		rs_json=json.loads(rs.text)
		#print(rs_json)
		json_dict_title = split.join(tuple(csv_title))
		# filename = get_desktop()+"\\交易明细记录"+str(int(time.time()))+".csv"
		G_MaxPage = rs_json["data"]["totalPages"]
		G_MaxRecord = rs_json["data"]["totalCount"]
		self.info_lable.setText("找到" + str(G_MaxRecord) + "条记录,共" + str(G_MaxPage) + "页")
		recordlist = []
		self.info_progressbar.setRange(0,G_MaxPage)
		QApplication.processEvents()
		for ipage in range(1, G_MaxPage + 1, 1):
			params_dict["pageNum"] = ipage
			#print("当前第" + str(ipage) + "页")
			self.info_progressbar.setValue(ipage)
			self.stb_info.showMessage("正在处理数据，请稍后")
			QApplication.processEvents()
			rs_all = webRequest("get",G_Url,G_Refer,params_dict,"detail_list")
			# print(rs_all)
			rs_all_json=json.loads(rs_all.text)
			json_dict = rs_all_json["data"]["items"]
			for json_dict_data in json_dict:
				rlist = []
				rlist.append(json_dict_data["orderNo"].strip() + "\t")  # 0
				rlist.append("")  # 1
				rlist.append(json_dict_data["phoneNo"].strip() + "\t")  # 2
				rlist.append(json_dict_data["memberId"].strip() + "\t")  # 3
				rlist.append("")  # 4
				rlist.append(json_orderstates[str(json_dict_data["orderStatus"])])  # 5
				json_timestamp = json_dict_data["orderTradeTime"] / 1000
				# print(json_timestamp)
				json_dict_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(json_timestamp))
				rlist.append(json_dict_time)  # 6
				rlist.append(json_dict_data["storeId"].strip() + "\t")  # 7
				rlist.append(json_dict_data["storeName"].strip() + "\t")  # 8
				rlist.append("")  # 9
				rlist.append("")  # 10
				rlist.append(str(round(float(json_dict_data["orderAmt"]) / 100, 2)))  # 11
				try:
					json_dict_data_cash = json_dict_data["ext"]
					json_cash_data = json.loads(json_dict_data_cash)
					rlist.append(str(round(float(json_cash_data["cashFee"]) / 100, 2)))  # 12
				except:
					rlist.append("0.00")
				try:
					json_cash_discount = round(float(json_dict_data["orderAmt"] - json_cash_data["cashFee"]) / 100, 2)
					# print(json_cash_discount)
					rlist.append(str(json_cash_discount))  # 13
				except:
					rlist.append("0.00")  # 13
				rlist.append(json_ordertype[json_dict_data["orderType"]])  # 14
				rlist.append("")  # 15

				if rlist[14] == "1":
					json_dict_data_protype = json_producttype[str(json_dict_data["productInfo"][0]["productType"])]
					rlist[14] = json_dict_data_protype

				if str(json_dict_data["orderStatus"]) == "70":
					rlist[12] = "0.00"
					rlist[13] = "0.00"

				if rlist not in recordlist:
					recordlist.append(rlist)
		try:
			with open(csv_filename, "w", newline="") as datacsv:
				dwrite = csv.writer(datacsv)
				dwrite.writerow(csv_title)
				dwrite.writerows(recordlist)
				self.stb_info.showMessage("数据成功导出到桌面，文件名为："+csv_name)
		except:
			with open(csv_sec_filename, "w", newline="") as datacsv:
				dwrite = csv.writer(datacsv)
				dwrite.writerow(csv_title)
				dwrite.writerows(recordlist)
				self.stb_info.showMessage("数据成功导出到桌面，文件名为：" + csv_sec_name)
	pass


if __name__ == "__main__":
	# 每一pyqt5应用程序必须创建一个应用程序对象。sys.argv参数是一个列表，从命令行输入参数。
	app = QApplication(sys.argv)
	myWin = MyMainWindow()
	# 显示在屏幕上
	myWin.show()
	# 系统exit()方法确保应用程序干净的退出
	# 的exec_()方法有下划线。因为执行是一个Python关键词。因此，exec_()代替
	sys.exit(app.exec_())