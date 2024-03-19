#Zoho Final
from django.shortcuts import render,redirect
from Register_Login.models import *
from Register_Login.views import logout
from django.contrib import messages
from django.conf import settings
from datetime import date
from datetime import datetime, timedelta
from Company_Staff.models import *
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import FileResponse, JsonResponse
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from xhtml2pdf import pisa
from django.template.loader import get_template
from bs4 import BeautifulSoup
import io,os
import pandas as pd
from openpyxl import Workbook
from openpyxl import load_workbook
from django.http import HttpResponse,HttpResponseRedirect
from io import BytesIO
from django.db.models import Max
from django.db.models import Q
from django.http import JsonResponse,HttpResponse,HttpResponseRedirect

# Create your views here.



# -------------------------------Company section--------------------------------
# company dashboard
def company_dashboard(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')

        # Calculate the date 20 days before the end date for payment term renew and 10 days before for trial period renew
        if dash_details.payment_term:
            reminder_date = dash_details.End_date - timedelta(days=20)
        else:
            reminder_date = dash_details.End_date - timedelta(days=10)
        current_date = date.today()
        alert_message = current_date >= reminder_date
        
        payment_request = True if PaymentTermsUpdates.objects.filter(company=dash_details,update_action=1,status='Pending').exists() else False

        # Calculate the number of days between the reminder date and end date
        days_left = (dash_details.End_date - current_date).days
        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'alert_message':alert_message,
            'days_left':days_left,
            'payment_request':payment_request,
        }
        return render(request, 'company/company_dash.html', context)
    else:
        return redirect('/')
    
    
# def company_dashboard(request):
#     if 'login_id' in request.session:
#         log_id = request.session['login_id']
#         if 'login_id' not in request.session:
#             return redirect('/')
#         log_details= LoginDetails.objects.get(id=log_id)
#         dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
#         allmodules= ZohoModules.objects.get(company=dash_details,status='New')

#         # Calculate the date 20 days before the end date for payment term renew
#         reminder_date = dash_details.End_date - timedelta(days=20)
#         current_date = date.today()
#         alert_message = current_date >= reminder_date
        
#         payment_request = True if PaymentTermsUpdates.objects.filter(company=dash_details,update_action=1,status='Pending').exists() else False

#         # Calculate the number of days between the reminder date and end date
#         days_left = (dash_details.End_date - current_date).days
#         context = {
#             'details': dash_details,
#             'allmodules': allmodules,
#             'alert_message':alert_message,
#             'days_left':days_left,
#             'payment_request':payment_request,
#         }
#         return render(request, 'company/company_dash.html', context)
#     else:
#         return redirect('/')


# company staff request for login approval
def company_staff_request(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        staff_request=StaffDetails.objects.filter(company=dash_details.id, company_approval=0).order_by('-id')
        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'requests':staff_request,
        }
        return render(request, 'company/staff_request.html', context)
    else:
        return redirect('/')

# company staff accept or reject
def staff_request_accept(request,pk):
    staff=StaffDetails.objects.get(id=pk)
    staff.company_approval=1
    staff.save()
    return redirect('company_staff_request')

def staff_request_reject(request,pk):
    staff=StaffDetails.objects.get(id=pk)
    login_details=LoginDetails.objects.get(id=staff.company.id)
    login_details.delete()
    staff.delete()
    return redirect('company_staff_request')


# All company staff view, cancel staff approval
def company_all_staff(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        all_staffs=StaffDetails.objects.filter(company=dash_details.id, company_approval=1).order_by('-id')
       
        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'staffs':all_staffs,
        }
        return render(request, 'company/all_staff_view.html', context)
    else:
        return redirect('/')

def staff_approval_cancel(request, pk):
    """
    Sets the company approval status to 2 for the specified staff member, effectively canceling staff approval.

    This function is designed to be used for canceling staff approval, and the company approval value is set to 2.
    This can be useful for identifying resigned staff under the company in the future.

    """
    staff = StaffDetails.objects.get(id=pk)
    staff.company_approval = 2
    staff.save()
    return redirect('company_all_staff')


# company profile, profile edit
def company_profile(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        terms=PaymentTerms.objects.all()
        payment_history=dash_details.previous_plans.all()

        # Calculate the date 20 days before the end date
        reminder_date = dash_details.End_date - timedelta(days=20)
        current_date = date.today()
        renew_button = current_date >= reminder_date

        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'renew_button': renew_button,
            'terms':terms,
            'payment_history':payment_history,
        }
        return render(request, 'company/company_profile.html', context)
    else:
        return redirect('/')

def company_profile_editpage(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        context = {
            'details': dash_details,
            'allmodules': allmodules
        }
        return render(request, 'company/company_profile_editpage.html', context)
    else:
        return redirect('/')

def company_profile_basicdetails_edit(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details= LoginDetails.objects.get(id=log_id)
        if request.method == 'POST':
            # Get data from the form
            log_details.first_name = request.POST.get('fname')
            log_details.last_name = request.POST.get('lname')
            log_details.email = request.POST.get('eid')
            log_details.username = request.POST.get('uname')
            log_details.save()
            messages.success(request,'Updated')
            return redirect('company_profile_editpage') 
        else:
            return redirect('company_profile_editpage') 

    else:
        return redirect('/')
    
def company_password_change(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details= LoginDetails.objects.get(id=log_id)
        if request.method == 'POST':
            # Get data from the form
            password = request.POST.get('pass')
            cpassword = request.POST.get('cpass')
            if password == cpassword:
                if LoginDetails.objects.filter(password=password).exists():
                    messages.error(request,'Use another password')
                    return redirect('company_profile_editpage')
                else:
                    log_details.password=password
                    log_details.save()

            messages.success(request,'Password Changed')
            return redirect('company_profile_editpage') 
        else:
            return redirect('company_profile_editpage') 

    else:
        return redirect('/')
       
def company_profile_companydetails_edit(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details = LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)

        if request.method == 'POST':
            # Get data from the form
            gstno = request.POST.get('gstno')
            profile_pic = request.FILES.get('image')

            # Update the CompanyDetails object with form data
            dash_details.company_name = request.POST.get('cname')
            dash_details.contact = request.POST.get('phone')
            dash_details.address = request.POST.get('address')
            dash_details.city = request.POST.get('city')
            dash_details.state = request.POST.get('state')
            dash_details.country = request.POST.get('country')
            dash_details.pincode = request.POST.get('pincode')
            dash_details.pan_number = request.POST.get('pannumber')

            if gstno:
                dash_details.gst_no = gstno

            if profile_pic:
                dash_details.profile_pic = profile_pic

            dash_details.save()

            messages.success(request, 'Updated')
            return redirect('company_profile_editpage')
        else:
            return redirect('company_profile_editpage')
    else:
        return redirect('/')    

# company modules editpage
def company_module_editpage(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        context = {
            'details': dash_details,
            'allmodules': allmodules
        }
        return render(request, 'company/company_module_editpage.html', context)
    else:
        return redirect('/')

def company_module_edit(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')

        # Check for any previous module update request
        if ZohoModules.objects.filter(company=dash_details,status='Pending').exists():
            messages.warning(request,'You have a pending update request, wait for approval or contact our support team for any help..?')
            return redirect('company_profile')
        if request.method == 'POST':
            # Retrieve values
            items = request.POST.get('items', 0)
            price_list = request.POST.get('price_list', 0)
            stock_adjustment = request.POST.get('stock_adjustment', 0)
            godown = request.POST.get('godown', 0)

            cash_in_hand = request.POST.get('cash_in_hand', 0)
            offline_banking = request.POST.get('offline_banking', 0)
            upi = request.POST.get('upi', 0)
            bank_holders = request.POST.get('bank_holders', 0)
            cheque = request.POST.get('cheque', 0)
            loan_account = request.POST.get('loan_account', 0)

            customers = request.POST.get('customers', 0)
            invoice = request.POST.get('invoice', 0)
            estimate = request.POST.get('estimate', 0)
            sales_order = request.POST.get('sales_order', 0)
            recurring_invoice = request.POST.get('recurring_invoice', 0)
            retainer_invoice = request.POST.get('retainer_invoice', 0)
            credit_note = request.POST.get('credit_note', 0)
            payment_received = request.POST.get('payment_received', 0)
            delivery_challan = request.POST.get('delivery_challan', 0)

            vendors = request.POST.get('vendors', 0)
            bills = request.POST.get('bills', 0)
            recurring_bills = request.POST.get('recurring_bills', 0)
            vendor_credit = request.POST.get('vendor_credit', 0)
            purchase_order = request.POST.get('purchase_order', 0)
            expenses = request.POST.get('expenses', 0)
            recurring_expenses = request.POST.get('recurring_expenses', 0)
            payment_made = request.POST.get('payment_made', 0)

            projects = request.POST.get('projects', 0)

            chart_of_accounts = request.POST.get('chart_of_accounts', 0)
            manual_journal = request.POST.get('manual_journal', 0)

            eway_bill = request.POST.get('ewaybill', 0)

            employees = request.POST.get('employees', 0)
            employees_loan = request.POST.get('employees_loan', 0)
            holiday = request.POST.get('holiday', 0)
            attendance = request.POST.get('attendance', 0)
            salary_details = request.POST.get('salary_details', 0)

            reports = request.POST.get('reports', 0)

            update_action=1
            status='Pending'

            # Create a new ZohoModules instance and save it to the database
            data = ZohoModules(
                company=dash_details,
                items=items, price_list=price_list, stock_adjustment=stock_adjustment, godown=godown,
                cash_in_hand=cash_in_hand, offline_banking=offline_banking, upi=upi, bank_holders=bank_holders,
                cheque=cheque, loan_account=loan_account,
                customers=customers, invoice=invoice, estimate=estimate, sales_order=sales_order,
                recurring_invoice=recurring_invoice, retainer_invoice=retainer_invoice, credit_note=credit_note,
                payment_received=payment_received, delivery_challan=delivery_challan,
                vendors=vendors, bills=bills, recurring_bills=recurring_bills, vendor_credit=vendor_credit,
                purchase_order=purchase_order, expenses=expenses, recurring_expenses=recurring_expenses,
                payment_made=payment_made,
                projects=projects,
                chart_of_accounts=chart_of_accounts, manual_journal=manual_journal,
                eway_bill=eway_bill,
                employees=employees, employees_loan=employees_loan, holiday=holiday,
                attendance=attendance, salary_details=salary_details,
                reports=reports,update_action=update_action,status=status    
            )
            data.save()
            messages.success(request,"Request sent successfully. Please wait for approval.")
            return redirect('company_profile')
        else:
            return redirect('company_module_editpage')  
    else:
        return redirect('/')


def company_renew_terms(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)

        # Check for any previous  extension request
        if PaymentTermsUpdates.objects.filter(company=dash_details,update_action=1,status='Pending').exists():
            messages.warning(request,'You have a pending request, wait for approval or contact our support team for any help..?')
            return redirect('company_profile')
        if request.method == 'POST':
            select=request.POST['select']
            terms=PaymentTerms.objects.get(id=select)
            update_action=1
            status='Pending'
            newterms=PaymentTermsUpdates(
               company=dash_details,
               payment_term=terms,
               update_action=update_action,
               status=status 
            )
            newterms.save()
            messages.success(request,'Request sent successfully, Please wait for approval...')
            return redirect('company_profile')
        else:
            return redirect('company_profile')
    else:
        return redirect('/')

# company notifications and messages
def company_notifications(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        notifications = dash_details.notifications.filter(is_read=0).order_by('-date_created','-time')
        end_date = dash_details.End_date
        company_days_remaining = (end_date - date.today()).days
        payment_request = True if PaymentTermsUpdates.objects.filter(company=dash_details,update_action=1,status='Pending').exists() else False
        
        print(company_days_remaining)
        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'notifications':notifications,
            'days_remaining':company_days_remaining,
            'payment_request':payment_request,
        }

        return render(request,'company/company_notifications.html',context)
        
    else:
        return redirect('/')
        
        
def company_message_read(request,pk):
    '''
    message read functions set the is_read to 1, 
    by default it is 0 means not seen by user.

    '''
    notification=Notifications.objects.get(id=pk)
    notification.is_read=1
    notification.save()
    return redirect('company_notifications')
    
    
def company_payment_history(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/') 
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details,status='New')
        payment_history=dash_details.previous_plans.all()

        context = {
            'details': dash_details,
            'allmodules': allmodules,
            'payment_history':payment_history,
            
        }
        return render(request,'company/company_payment_history.html', context)
    else:
        return redirect('/')
        
def company_trial_feedback(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/') 
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
        trial_instance = TrialPeriod.objects.get(company=dash_details)
        if request.method == 'POST':
            interested = request.POST.get('interested')
            feedback=request.POST.get('feedback') 
            
            trial_instance.interested_in_buying=1 if interested =='yes' else 2
            trial_instance.feedback=feedback
            trial_instance.save()

            if interested =='yes':
                return redirect('company_profile')
            else:
                return redirect('company_dashboard')
        else:
            return redirect('company_dashboard')
    else:
        return redirect('/')
# -------------------------------Staff section--------------------------------

# staff dashboard
def staff_dashboard(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = StaffDetails.objects.get(login_details=log_details,company_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
        context={
            'details':dash_details,
            'allmodules': allmodules,
        }
        return render(request,'staff/staff_dash.html',context)
    else:
        return redirect('/')


# staff profile
def staff_profile(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = StaffDetails.objects.get(login_details=log_details,company_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
        context={
            'details':dash_details,
            'allmodules': allmodules,
        }
        return render(request,'staff/staff_profile.html',context)
    else:
        return redirect('/')


def staff_profile_editpage(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = StaffDetails.objects.get(login_details=log_details,company_approval=1)
        allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
        context = {
            'details': dash_details,
            'allmodules': allmodules
        }
        return render(request, 'staff/staff_profile_editpage.html', context)
    else:
        return redirect('/')

def staff_profile_details_edit(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details= LoginDetails.objects.get(id=log_id)
        dash_details = StaffDetails.objects.get(login_details=log_details,company_approval=1)
        if request.method == 'POST':
            # Get data from the form
            log_details.first_name = request.POST.get('fname')
            log_details.last_name = request.POST.get('lname')
            log_details.email = request.POST.get('eid')
            log_details.username = request.POST.get('uname')
            log_details.save()
            dash_details.contact = request.POST.get('phone')
            old=dash_details.image
            new=request.FILES.get('profile_pic')
            print(new,old)
            if old!=None and new==None:
                dash_details.image=old
            else:
                print(new)
                dash_details.image=new
            dash_details.save()
            messages.success(request,'Updated')
            return redirect('staff_profile_editpage') 
        else:
            return redirect('staff_profile_editpage') 

    else:
        return redirect('/')

def staff_password_change(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details= LoginDetails.objects.get(id=log_id)
        if request.method == 'POST':
            # Get data from the form
            password = request.POST.get('pass')
            cpassword = request.POST.get('cpass')
            if password == cpassword:
                if LoginDetails.objects.filter(password=password).exists():
                    messages.error(request,'Use another password')
                    return redirect('staff_profile_editpage')
                else:
                    log_details.password=password
                    log_details.save()

            messages.success(request,'Password Changed')
            return redirect('staff_profile_editpage') 
        else:
            return redirect('staff_profile_editpage') 

    else:
        return redirect('/')


    
def company_gsttype_change(request):
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')

        log_details = LoginDetails.objects.get(id=log_id)
        dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)

        if request.method == 'POST':
            # Get data from the form
            
            gstno = request.POST.get('gstno')
            gsttype = request.POST.get('gsttype')

            # Check if gsttype is one of the specified values
            if gsttype in ['unregistered Business', 'Overseas', 'Consumer']:
                dash_details.gst_no = None
            else:
                if gstno:
                    dash_details.gst_no = gstno
                else:
                    messages.error(request,'GST Number is not entered*')
                    return redirect('company_profile_editpage')


            dash_details.gst_type = gsttype

            dash_details.save()
            messages.success(request,'GST Type changed')
            return redirect('company_profile_editpage')
        else:
            return redirect('company_profile_editpage')
    else:
        return redirect('/') 
    

# -------------------------------Zoho Modules section--------------------------------

    # ADRIAN LUIZ (GODOWN)

def list_godown(request):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            allmodules= ZohoModules.objects.get(company=dash_details,status='New')
            godown_obj = Godown.objects.filter(company = dash_details)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'godown_obj':godown_obj
            }
        
        if log_details.user_type == 'Staff':
            dash_details = StaffDetails.objects.get(login_details=log_details)
            godown_obj = Godown.objects.filter(company = dash_details.company)
            allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'godown_obj':godown_obj
            }

        return render(request, 'godown/godown_list.html', context)
    
def add_godown(request):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            allmodules= ZohoModules.objects.get(company=dash_details,status='New')
            item_obj = Items.objects.filter(company = dash_details)
            units = Unit.objects.filter(company = dash_details)
            accounts = Chart_of_Accounts.objects.filter(company=dash_details)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'item_obj':item_obj,
            'units':units,
            'accounts':accounts
            }
        
        if log_details.user_type == 'Staff':
            dash_details = StaffDetails.objects.get(login_details=log_details)
            allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
            item_obj = Items.objects.filter(company = dash_details.company)
            units = Unit.objects.filter(company = dash_details.company)
            accounts = Chart_of_Accounts.objects.filter(company=dash_details.company)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'item_obj':item_obj,
            'units':units,
            'accounts':accounts
            }

        return render(request, 'godown/add_godown.html', context)
    
def add_godown_func(request):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method == 'POST':
                date = request.POST.get('Date')
                item = request.POST.get('Item')
                gname = request.POST.get('Gname')
                gaddress = request.POST.get('Gaddress')
                stock = request.POST.get('Stock')
                distance = request.POST.get('Distance')
                item_obj = Items.objects.get(id=item)
                action = request.POST.get('save')
                godown = Godown(date=date,
                                item=item_obj,
                                stock_keeping=stock,
                                godown_name=gname,
                                godown_address=gaddress,
                                distance=distance,
                                stock_in_hand = item_obj.current_stock,
                                hsn = item_obj.hsn_code,
                                login_details=log_details,
                                company = company,
                                action = action)
                godown.save()

                godown_history = GodownHistory(company = company,
                                               login_details=log_details,
                                               godown=godown,
                                               date=date,
                                               action='Created')
                godown_history.save()


        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method == 'POST':
                date = request.POST.get('Date')
                item = request.POST.get('Item')
                gname = request.POST.get('Gname')
                gaddress = request.POST.get('Gaddress')
                stock = request.POST.get('Stock')
                distance = request.POST.get('Distance')
                item_obj = Items.objects.get(id=item)
                action = request.POST.get('save')
                godown = Godown(date=date,
                                item=item_obj,
                                stock_keeping=stock,
                                godown_name=gname,
                                godown_address=gaddress,
                                distance=distance,
                                stock_in_hand = item_obj.current_stock,
                                hsn = item_obj.hsn_code,
                                login_details=log_details,
                                company = company,
                                action = action)
                godown.save()

                godown_history = GodownHistory(company = company,
                                               login_details=log_details,
                                               godown=godown,
                                               date=date,
                                               action='Created')
                godown_history.save()

        
        messages.success(request,'Added Successfully')
        return redirect('add_godown')
    
def overview_page(request,pk):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            allmodules= ZohoModules.objects.get(company=dash_details,status='New')
            godown_obj = Godown.objects.filter(company = dash_details)
            p = Godown.objects.get(id = pk)
            godown_history = GodownHistory.objects.filter(godown=p)
            comment = GodownComments.objects.filter(godown=p)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'godown_obj':godown_obj,
            'p':p,
            'godown_history':godown_history,
            'comment':comment
            }
        
        if log_details.user_type == 'Staff':
            dash_details = StaffDetails.objects.get(login_details=log_details)
            godown_obj = Godown.objects.filter(company = dash_details.company)
            allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
            p = Godown.objects.get(id = pk)
            godown_history = GodownHistory.objects.filter(godown=p)
            comment = GodownComments.objects.filter(godown=p)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'godown_obj':godown_obj,
            'p':p,
            'godown_history':godown_history,
            'comment':comment
            }

        return render(request, 'godown/overview_page.html', context)

def edit_godown(request,pk):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            dash_details = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            allmodules= ZohoModules.objects.get(company=dash_details,status='New')
            item_obj = Items.objects.filter(company = dash_details)
            units = Unit.objects.filter(company = dash_details)
            godown_obj = Godown.objects.get(id=pk)
            accounts = Chart_of_Accounts.objects.filter(company=dash_details)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'item_obj':item_obj,
            'units':units,
            'accounts':accounts,
            'godown_obj':godown_obj
            }
        
        if log_details.user_type == 'Staff':
            dash_details = StaffDetails.objects.get(login_details=log_details)
            allmodules= ZohoModules.objects.get(company=dash_details.company,status='New')
            item_obj = Items.objects.filter(company = dash_details.company)
            units = Unit.objects.filter(company = dash_details.company)
            godown_obj = Godown.objects.get(id=pk)
            accounts = Chart_of_Accounts.objects.filter(company=dash_details.company)
            context = {
            'details': dash_details,
            'log_details':log_details,
            'dash_details':dash_details,
            'allmodules':allmodules,
            'item_obj':item_obj,
            'units':units,
            'accounts':accounts,
            'godown_obj':godown_obj
            }

        return render(request, 'godown/edit_godown.html', context)
    
def edit_godown_func(request):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method == 'POST':
                godown_id = request.POST.get('godown_id')
                date = request.POST.get('Date')
                item = request.POST.get('Item')
                gname = request.POST.get('Gname')
                gaddress = request.POST.get('Gaddress')
                stock = request.POST.get('Stock')
                distance = request.POST.get('Distance')
                item_obj = Items.objects.get(id=item)
                godown = Godown.objects.get(id=godown_id)
                godown.date=date
                godown.item=item_obj
                godown.stock_keeping=stock
                godown.godown_name=gname
                godown.godown_address=gaddress
                godown.distance=distance
                godown.stock_in_hand = item_obj.current_stock
                godown.hsn = item_obj.hsn_code
                godown.login_details=log_details
                godown.company = company

                godown.save()

                godown_history = GodownHistory(company = company,
                                               login_details=log_details,
                                               godown=godown,
                                               date=date,
                                               action='Edited')
                godown_history.save()

        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method == 'POST':
                godown_id = request.POST.get('godown_id')
                date = request.POST.get('Date')
                item = request.POST.get('Item')
                gname = request.POST.get('Gname')
                gaddress = request.POST.get('Gaddress')
                stock = request.POST.get('Stock')
                distance = request.POST.get('Distance')
                item_obj = Items.objects.get(id=item)
                godown = Godown.objects.get(id=godown_id)
                godown.date=date
                godown.item=item_obj
                godown.stock_keeping=stock
                godown.godown_name=gname
                godown.godown_address=gaddress
                godown.distance=distance
                godown.stock_in_hand = item_obj.current_stock
                godown.hsn = item_obj.hsn_code
                godown.login_details=log_details
                godown.company = company

                godown.save()

                godown_history = GodownHistory(company = company,
                                               login_details=log_details,
                                               godown=godown,
                                               date=date,
                                               action='Edited')
                godown_history.save()
        
        messages.success(request,'Edited Successfully')
        return redirect('list_godown')
    
def newitem(request):

    return render(request,'godown/try.html')


def change_status(request, pk):

    godown_obj = Godown.objects.get(id=pk)
    if godown_obj.status == 'Active':
        godown_obj.status='Inactive'
    else:
        godown_obj.status='Active'
    godown_obj.save()
    return redirect('overview_page',pk=pk)

def change_action(request, pk):

    godown_obj = Godown.objects.get(id=pk)
    godown_obj.action='Adjusted'
    godown_obj.save()
    return redirect('overview_page',pk=pk)

def AddComment(request,pk):

    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        godown = Godown.objects.get(id=pk)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            
            if request.method == 'POST':
                comments = request.POST.get('comments')
                comment = GodownComments(
                                login_details=log_details,
                                company = company,
                                godown = godown,
                                comment = comments)
                comment.save()


        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method == 'POST':
                comments = request.POST.get('comments')
                comment = GodownComments(
                                login_details=log_details,
                                company = company,
                                godown = godown,
                                comment = comments)
                comment.save()
        
        messages.success(request,'Added Comment Successfully')
        return redirect('overview_page',pk=pk)
    
def AddFile(request, pk):

    godown_obj = Godown.objects.get(id=pk)
    if request.method == 'POST':
        file = request.FILES.get('file')
        godown_obj.file=file
        godown_obj.save()
    messages.success(request,'Added File Successfully')
    return redirect('overview_page',pk=pk)

def file_download(request,pk):
    godown_obj= Godown.objects.get(id=pk)
    file = godown_obj.file
    response = FileResponse(file)
    response['Content-Disposition'] = f'attachment; filename="{file.name}"'
    return response

def ShareEmail(request,pk):
    try:
            if request.method == 'POST':
                emails_string = request.POST['email']

    
                emails_list = [email.strip() for email in emails_string.split(',')]
                print(emails_list)
                p=Godown.objects.get(id=pk)
                        
                context = {'p':p}
                template_path = 'godown/overview_page.html'
                template = get_template(template_path)
                html  = template.render(context)
                result = BytesIO()
                pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
                pdf = result.getvalue()
                filename = f'{p.godown_name}details - {p.id}.pdf'
                subject = f"{p.godown_name}{p.godown_address}  - {p.id}-details"
                email = EmailMessage(subject, f"Hi,\nPlease find the attached godown details - File-{p.godown_name}{p.godown_address} .\n--\nRegards,\n", from_email=settings.EMAIL_HOST_USER, to=emails_list)
                email.attach(filename, pdf, "application/pdf")
                email.send(fail_silently=False)
                messages.success(request, 'over view page has been shared via email successfully..!')
                return redirect('overview_page',pk=pk)
    except Exception as e:
            print(e)
            messages.error(request, f'{e}')
            return redirect('overview_page',pk=pk)
    
    
def DeleteComment(request,pk):
        
    comment = GodownComments.objects.get(id=pk)
    comment.delete()

    messages.success(request,'Deleted Comment Successfully')
    return redirect('overview_page',pk=pk)

def Add_Item(request):                                                                #new by tinto mt
    
    login_id = request.session['login_id']
    if 'login_id' not in request.session:
        return redirect('/')
    log_user = LoginDetails.objects.get(id=login_id)
    if log_user.user_type == 'Company':
        company_id = request.session['login_id']
        
        if request.method=='POST':
            a=Items()
            b=Item_Transaction_History()
            c = CompanyDetails.objects.get(login_details=company_id)
            b.company=c
            b.Date=date.today()
            b.logindetails=log_user
            a.login_details=log_user
            a.company=c
            a.item_type = request.POST.get("type",None)
            a.item_name = request.POST.get("name",None)
            unit_id = request.POST.get("unit")
            uid=Unit.objects.get(id=unit_id)
            # unit_instance = get_object_or_404(Unit, id=unit_id)
            a.unit = uid
            a.hsn_code = request.POST.get("hsn",None)
            a.tax_reference = request.POST.get("radio",None)
            a.intrastate_tax = request.POST.get("intra",None)
            a.interstate_tax= request.POST.get("inter",None)
            a.selling_price = request.POST.get("sel_price",None)
            a.sales_account = request.POST.get("sel_acc",None)
            a.sales_description = request.POST.get("sel_desc",None)
            a.purchase_price = request.POST.get("cost_price",None)
            a.purchase_account = request.POST.get("cost_acc",None)
            a.purchase_description = request.POST.get("pur_desc",None)
            # track = request.POST.get("trackState",None)
            track_state_value = request.POST.get("trackstate", None)

# Check if the checkbox is checked
            if track_state_value == "on":
                a.track_inventory = 1
            else:
                a.track_inventory = 0

            
            minstock=request.POST.get("minimum_stock",None)
            if minstock != "":
                a.minimum_stock_to_maintain = request.POST.get("minimum_stock",None)
            else:
                a.minimum_stock_to_maintain = 0
            a.activation_tag = 'Active'
            a.type = 'Opening Stock'
            a.inventory_account = request.POST.get("invacc",None)
            a.opening_stock = request.POST.get("openstock",None)
            a.current_stock=request.POST.get("openstock",None)
            a.opening_stock_per_unit = request.POST.get("rate",None)
            item_name= request.POST.get("name",None)
            hsncode=request.POST.get("hsn",None)
            
            if Items.objects.filter(item_name=item_name, company=c).exists():
                error='yes'
                messages.error(request,'Item with same name exsits !!!')
                return redirect('add_godown')
            elif Items.objects.filter(hsn_code=hsncode, company=c).exists():
                error='yes'
                messages.error(request,'Item with same  hsn code exsits !!!')
                return redirect('add_godown')
            else:
                a.save()    
                t=Items.objects.get(id=a.id)
                b.items=t
                b.save()
                messages.success(request,'Item Added Successfully !!!')
                return redirect('add_godown')
    elif log_user.user_type == 'Staff':
        staff_id = request.session['login_id']
        if request.method=='POST':
            a=Items()
            b=Item_Transaction_History()
            staff = LoginDetails.objects.get(id=staff_id)
            sf = StaffDetails.objects.get(login_details=staff)
            c=sf.company
            b.Date=date.today()
            b.company=c
            b.logindetails=log_user
            a.login_details=log_user
            a.company=c
            a.item_type = request.POST.get("type",None)
            a.item_name = request.POST.get("name",None)
            unit_id = request.POST.get("unit")
            unit_instance = get_object_or_404(Unit, id=unit_id)
            a.unit = unit_instance
            a.hsn_code = request.POST.get("hsn",None)
            a.tax_reference = request.POST.get("radio",None)
            a.intrastate_tax = request.POST.get("intra",None)
            a.interstate_tax= request.POST.get("inter",None)
            a.selling_price = request.POST.get("sel_price",None)
            a.sales_account = request.POST.get("sel_acc",None)
            a.sales_description = request.POST.get("sel_desc",None)
            a.purchase_price = request.POST.get("cost_price",None)
            a.purchase_account = request.POST.get("cost_acc",None)
            a.purchase_description = request.POST.get("pur_desc",None)
            # track_state_value = request.POST.get("trackState", None)

            track_state_value = request.POST.get("trackstate", None)

            # Check if the checkbox is checked
            if track_state_value == "on":
                a.track_inventory = 1
            else:
                a.track_inventory = 0
            minstock=request.POST.get("minimum_stock",None)
            item_name= request.POST.get("name",None)
            hsncode=request.POST.get("hsn",None)
            
            if minstock != "":
                a.minimum_stock_to_maintain = request.POST.get("minimum_stock",None)
            else:
                a.minimum_stock_to_maintain = 0
            # a.activation_tag = request.POST.get("status",None)
            a.activation_tag = 'Active'
            a.type = 'Opening Stock'
            a.inventory_account = request.POST.get("invacc",None)
            a.opening_stock = request.POST.get("openstock",None)
            a.current_stock=request.POST.get("openstock",None)
            a.opening_stock_per_unit = request.POST.get("rate",None)
        
        

        
            if Items.objects.filter(item_name=item_name,company=c).exists():
                error='yes'
                messages.error(request,'Item with same name exsits !!!')
                return redirect('add_godown')
                
            elif Items.objects.filter(hsn_code=hsncode, company=c).exists():
                error='yes'
                messages.error(request,'Item with same  hsn code exsits !!!')
                return redirect('add_godown')
            else:
                a.save()    
                t=Items.objects.get(id=a.id)
                b.items=t
                b.save()
                messages.success(request,'Item Added Successfully !!!')
                return redirect('add_godown')
    return redirect('add_godown')

def godownmodal_unit(request):
    
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method=='POST':
                units =request.POST.get('unit')
                unit_obj = Unit(unit_name=units,
                        company=company)
                unit_obj.save()
                id = unit_obj.id
                return JsonResponse({'status': 'success', 'message': 'Unit added successfully', 'id':id})

        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method=='POST':
                units =request.POST.get('unit')
            
                unit_obj = Unit(unit_name=units,
                        company=company)
                unit_obj.save()
                id = unit_obj.id
                
                return JsonResponse({'status': 'success', 'message': 'Unit added successfully', 'id':id})


def godownunit_dropdown(request):

    options = {}
    option_objects = Unit.objects.all()
    for option in option_objects:
        options[option.id] = [option.unit_name,option.id]
    print(options)
    return JsonResponse(options)
    
def AddAccount(request):
    
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method=='POST':
                account_type =request.POST.get('acctype')
                account_name =request.POST.get('accName')
                account_code =request.POST.get('accCode')
                
                description =request.POST.get('desc')
            
                accounts = Chart_of_Accounts(account_type=account_type,
                                             account_name=account_name,
                                             description=description,
                                             
                                             account_code=account_code,
                                             company=company,
                                             login_details=log_details)
                accounts.save()
                id = accounts.id
              
        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method=='POST':
                account_type =request.POST.get('acctype')
                account_name =request.POST.get('accName')
                account_code =request.POST.get('accCode')
                
                description =request.POST.get('desc')
            
                accounts = Chart_of_Accounts(account_type=account_type,
                                             account_name=account_name,
                                             description=description,
                                             
                                             account_code=account_code,
                                             company=company,
                                             login_details=log_details)
                accounts.save()
                id = accounts.id
             
        return JsonResponse({'status': 'success', 'message': 'Unit added successfully', 'id':id})
    

def Add_Item_Edit(request,pk):                                                                #new by tinto mt
    
    login_id = request.session['login_id']
    if 'login_id' not in request.session:
        return redirect('/')
    log_user = LoginDetails.objects.get(id=login_id)
    if log_user.user_type == 'Company':
        company_id = request.session['login_id']
        
        if request.method=='POST':
            a=Items()
            b=Item_Transaction_History()
            c = CompanyDetails.objects.get(login_details=company_id)
            b.company=c
            b.Date=date.today()
            b.logindetails=log_user
            a.login_details=log_user
            a.company=c
            a.item_type = request.POST.get("type",None)
            a.item_name = request.POST.get("name",None)
            unit_id = request.POST.get("unit")
            uid=Unit.objects.get(id=unit_id)
            # unit_instance = get_object_or_404(Unit, id=unit_id)
            a.unit = uid
            a.hsn_code = request.POST.get("hsn",None)
            a.tax_reference = request.POST.get("radio",None)
            a.intrastate_tax = request.POST.get("intra",None)
            a.interstate_tax= request.POST.get("inter",None)
            a.selling_price = request.POST.get("sel_price",None)
            a.sales_account = request.POST.get("sel_acc",None)
            a.sales_description = request.POST.get("sel_desc",None)
            a.purchase_price = request.POST.get("cost_price",None)
            a.purchase_account = request.POST.get("cost_acc",None)
            a.purchase_description = request.POST.get("pur_desc",None)
            # track = request.POST.get("trackState",None)
            track_state_value = request.POST.get("trackstate", None)

# Check if the checkbox is checked
            if track_state_value == "on":
                a.track_inventory = 1
            else:
                a.track_inventory = 0

            
            minstock=request.POST.get("minimum_stock",None)
            if minstock != "":
                a.minimum_stock_to_maintain = request.POST.get("minimum_stock",None)
            else:
                a.minimum_stock_to_maintain = 0
            a.activation_tag = 'Active'
            a.type = 'Opening Stock'
            a.inventory_account = request.POST.get("invacc",None)
            a.opening_stock = request.POST.get("openstock",None)
            a.current_stock=request.POST.get("openstock",None)
            a.opening_stock_per_unit = request.POST.get("rate",None)
            item_name= request.POST.get("name",None)
            hsncode=request.POST.get("hsn",None)
            
            if Items.objects.filter(item_name=item_name, company=c).exists():
                error='yes'
                messages.error(request,'Item with same name exsits !!!')
                return redirect('edit_godown',pk=pk)
            elif Items.objects.filter(hsn_code=hsncode, company=c).exists():
                error='yes'
                messages.error(request,'Item with same  hsn code exsits !!!')
                return redirect('edit_godown',pk=pk)
            else:
                a.save()    
                t=Items.objects.get(id=a.id)
                b.items=t
                b.save()
                messages.success(request,'Item Added Successfully !!!')
                return redirect('edit_godown',pk=pk)
    elif log_user.user_type == 'Staff':
        staff_id = request.session['login_id']
        if request.method=='POST':
            a=Items()
            b=Item_Transaction_History()
            staff = LoginDetails.objects.get(id=staff_id)
            sf = StaffDetails.objects.get(login_details=staff)
            c=sf.company
            b.Date=date.today()
            b.company=c
            b.logindetails=log_user
            a.login_details=log_user
            a.company=c
            a.item_type = request.POST.get("type",None)
            a.item_name = request.POST.get("name",None)
            unit_id = request.POST.get("unit")
            unit_instance = get_object_or_404(Unit, id=unit_id)
            a.unit = unit_instance
            a.hsn_code = request.POST.get("hsn",None)
            a.tax_reference = request.POST.get("radio",None)
            a.intrastate_tax = request.POST.get("intra",None)
            a.interstate_tax= request.POST.get("inter",None)
            a.selling_price = request.POST.get("sel_price",None)
            a.sales_account = request.POST.get("sel_acc",None)
            a.sales_description = request.POST.get("sel_desc",None)
            a.purchase_price = request.POST.get("cost_price",None)
            a.purchase_account = request.POST.get("cost_acc",None)
            a.purchase_description = request.POST.get("pur_desc",None)
            # track_state_value = request.POST.get("trackState", None)

            track_state_value = request.POST.get("trackstate", None)

            # Check if the checkbox is checked
            if track_state_value == "on":
                a.track_inventory = 1
            else:
                a.track_inventory = 0
            minstock=request.POST.get("minimum_stock",None)
            item_name= request.POST.get("name",None)
            hsncode=request.POST.get("hsn",None)
            
            if minstock != "":
                a.minimum_stock_to_maintain = request.POST.get("minimum_stock",None)
            else:
                a.minimum_stock_to_maintain = 0
            # a.activation_tag = request.POST.get("status",None)
            a.activation_tag = 'Active'
            a.type = 'Opening Stock'
            a.inventory_account = request.POST.get("invacc",None)
            a.opening_stock = request.POST.get("openstock",None)
            a.current_stock=request.POST.get("openstock",None)
            a.opening_stock_per_unit = request.POST.get("rate",None)
        
        

        
            if Items.objects.filter(item_name=item_name,company=c).exists():
                error='yes'
                messages.error(request,'Item with same name exsits !!!')
                return redirect('edit_godown',pk=pk)
                
            elif Items.objects.filter(hsn_code=hsncode, company=c).exists():
                error='yes'
                messages.error(request,'Item with same  hsn code exsits !!!')
                return redirect('edit_godown',pk=pk)
            else:
                a.save()    
                t=Items.objects.get(id=a.id)
                b.items=t
                b.save()
                messages.success(request,'Item Added Successfully !!!')
                return redirect('edit_godown',pk=pk)
    return redirect('edit_godown',pk=pk)

def godownmodal_unit_edit(request,pk):
    
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method=='POST':
                units =request.POST.get('unit_name')
            
                unit_obj = Unit(unit_name=units,
                            company=company)
                unit_obj.save()
                

        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method=='POST':
                units =request.POST.get('unit_name')
                
        
                unit_obj = Unit(unit_name=units,
                        company=company)
                unit_obj.save()
               
        return redirect('edit_godown',pk)
    
    
def Add_Account_Edit(request,pk):
    
    if 'login_id' in request.session:
        log_id = request.session['login_id']
        if 'login_id' not in request.session:
            return redirect('/')
        log_details= LoginDetails.objects.get(id=log_id)
        if log_details.user_type == 'Company':
            company = CompanyDetails.objects.get(login_details=log_details,superadmin_approval=1,Distributor_approval=1)
            if request.method=='POST':
                account_type =request.POST.get('acctype')
                account_name =request.POST.get('accName')
                account_code =request.POST.get('accCode')
                
                description =request.POST.get('desc')
            
                accounts = Chart_of_Accounts(account_type=account_type,
                                             account_name=account_name,
                                             description=description,
                                             
                                             account_code=account_code,
                                             company=company,
                                             login_details=log_details)
                accounts.save()
                id = accounts.id

        if log_details.user_type == 'Staff':
            staff = StaffDetails.objects.get(login_details=log_details)
            company = staff.company
            if request.method=='POST':
                account_type =request.POST.get('acctype')
                account_name =request.POST.get('accName')
                account_code =request.POST.get('accCode')
                
                description =request.POST.get('desc')
            
                accounts = Chart_of_Accounts(account_type=account_type,
                                             account_name=account_name,
                                             description=description,
                                             
                                             account_code=account_code,
                                             company=company,
                                             login_details=log_details)
                accounts.save()
                id = accounts.id
             
        return JsonResponse({'status': 'success', 'message': 'Unit added successfully', 'id':id})
    


def delete_godown(request,pk):

    godown = Godown.objects.get(id=pk)
    godown.delete()
    messages.success(request,'Deleted Successfully')
    return redirect('list_godown')


    